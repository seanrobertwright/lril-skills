#!/usr/bin/env node
/**
 * Turn a help-me checklist (JSON) into one self-contained web page and open it.
 *
 *     node build-checklist.mjs path/to/checklist.json [--no-open] [-q]
 *     node build-checklist.mjs --list | --open <slug> | --done <slug>
 *
 * No dependencies. Nothing is served and nothing keeps running: the page is a
 * single file, and ticks are remembered by the browser. The checklist itself is
 * kept in a folder in the home directory (see storeDir) so it can be listed and
 * reopened in a later conversation. See ../checklist-format.md.
 */

import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ASSETS = path.join(HERE, 'assets');

export const MAX_STEPS = 40;
const MAX_TEXT = 4000;

export class ChecklistError extends Error {}

/* ------------------------------------------------------------- validation */

function text(value, where, { required = false, max = MAX_TEXT } = {}) {
  if (value === undefined || value === null) {
    if (required) throw new ChecklistError(`${where} is missing`);
    return '';
  }
  if (typeof value !== 'string') throw new ChecklistError(`${where} must be text`);
  const trimmed = value.trim();
  if (required && !trimmed) throw new ChecklistError(`${where} is empty`);
  if (trimmed.length > max) throw new ChecklistError(`${where} is longer than ${max} characters`);
  return trimmed;
}

function isPlainObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function list(value, where) {
  if (value === undefined || value === null) return [];
  if (!Array.isArray(value)) throw new ChecklistError(`${where} must be a list`);
  return value;
}

/** Links may only go to the web or to an email address. */
export function safeHref(url) {
  const trimmed = String(url ?? '').trim();
  return /^(https?:\/\/|mailto:)/i.test(trimmed) ? trimmed : '';
}

/** Check the checklist and return a clean copy. Throws ChecklistError with a plain message. */
export function validateChecklist(raw) {
  if (!isPlainObject(raw)) throw new ChecklistError('the checklist must be a JSON object');

  const out = {
    title: text(raw.title, 'title', { required: true, max: 200 }),
    summary: text(raw.summary, 'summary', { required: true }),
    source: text(raw.source, 'source', { max: 300 }),
    sourceUrl: '',
    minutes: null,
    before: [],
    words: [],
    steps: [],
  };

  const sourceUrl = text(raw.sourceUrl, 'sourceUrl', { max: 2000 });
  if (sourceUrl) {
    out.sourceUrl = safeHref(sourceUrl);
    if (!out.sourceUrl) throw new ChecklistError('sourceUrl must start with http://, https:// or mailto:');
  }

  if (raw.minutes !== undefined && raw.minutes !== null) {
    if (!Number.isInteger(raw.minutes) || raw.minutes < 1 || raw.minutes > 6000) {
      throw new ChecklistError('minutes must be a whole number from 1 to 6000');
    }
    out.minutes = raw.minutes;
  }

  out.before = list(raw.before, 'before').map((item, i) =>
    text(item, `before[${i + 1}]`, { required: true }));

  out.words = list(raw.words, 'words').map((item, i) => {
    if (!isPlainObject(item)) throw new ChecklistError(`words[${i + 1}] must be an object with word and meaning`);
    return {
      word: text(item.word, `words[${i + 1}].word`, { required: true, max: 100 }),
      meaning: text(item.meaning, `words[${i + 1}].meaning`, { required: true }),
    };
  });

  const steps = list(raw.steps, 'steps');
  if (!steps.length) throw new ChecklistError('steps is empty: a checklist needs at least one step');
  if (steps.length > MAX_STEPS) {
    throw new ChecklistError(`there are ${steps.length} steps; the most a page can hold is ${MAX_STEPS}. Split the task into two checklists.`);
  }

  const seen = new Map();
  out.steps = steps.map((item, i) => {
    const where = `step ${i + 1}`;
    if (!isPlainObject(item)) throw new ChecklistError(`${where} must be an object`);
    const step = {
      title: text(item.title, `${where} title`, { required: true, max: 200 }),
      do: text(item.do, `${where} do`, { required: true }),
      why: text(item.why, `${where} why`, { required: true, max: 1200 }),
      expect: text(item.expect, `${where} expect`),
      stuck: text(item.stuck, `${where} stuck`),
      warning: text(item.warning, `${where} warning`),
      group: text(item.group, `${where} group`, { max: 120 }),
      paste: null,
    };
    if (item.paste !== undefined && item.paste !== null) {
      if (!isPlainObject(item.paste)) throw new ChecklistError(`${where} paste must be an object with text and into`);
      if (typeof item.paste.text !== 'string' || !item.paste.text.trim()) {
        throw new ChecklistError(`${where} paste.text is missing`);
      }
      if (item.paste.text.length > MAX_TEXT) {
        throw new ChecklistError(`${where} paste.text is longer than ${MAX_TEXT} characters`);
      }
      step.paste = {
        // kept exactly as written: this is what lands on the clipboard
        text: item.paste.text.replace(/\r\n/g, '\n').replace(/^\n+|\s+$/g, ''),
        into: text(item.paste.into, `${where} paste.into`, { required: true, max: 120 }),
      };
    }
    const key = step.title.toLowerCase();
    if (seen.has(key)) {
      throw new ChecklistError(`step ${seen.get(key)} and ${where} have the same title ("${step.title}"); give each step its own title`);
    }
    seen.set(key, i + 1);
    return step;
  });

  return out;
}

/* ----------------------------------------------------------------- render */

export function esc(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

const INLINE_SRC = '`([^`]+)`|\\[([^\\]]+)\\]\\(([^)\\s]+)\\)|\\*\\*([^*]+)\\*\\*';

/** `code`, **bold** and [links](https://...) only; everything else is escaped. */
export function inline(source) {
  const re = new RegExp(INLINE_SRC, 'g');
  let out = '';
  let last = 0;
  let m;
  while ((m = re.exec(source)) !== null) {
    out += esc(source.slice(last, m.index));
    if (m[1] !== undefined) out += `<code>${esc(m[1])}</code>`;
    else if (m[2] !== undefined) {
      const href = safeHref(m[3]);
      out += href
        ? `<a href="${esc(href)}" target="_blank" rel="noopener noreferrer">${inline(m[2])}</a>`
        : esc(m[0]);
    } else out += `<strong>${inline(m[4])}</strong>`;
    last = re.lastIndex;
  }
  return out + esc(source.slice(last));
}

/** Blank lines separate paragraphs; a single newline is a line break. */
export function paragraphs(source) {
  return source
    .replace(/\r\n/g, '\n')
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter(Boolean)
    .map((p) => `<p>${p.split('\n').map((l) => inline(l.trim())).join('<br>')}</p>`)
    .join('\n');
}

function stepKey(title) {
  return createHash('sha256').update(title.toLowerCase()).digest('hex').slice(0, 12);
}

function renderStep(step, index) {
  const n = index + 1;
  const id = `step-${n}`;
  const parts = [];
  parts.push(`<li class="step" id="${id}" data-key="${stepKey(step.title)}" data-n="${n}" data-title="${esc(step.title)}">`);
  parts.push('<div class="step-head">');
  parts.push(`<input type="checkbox" class="tick" id="${id}-tick">`);
  parts.push(`<label class="step-title" for="${id}-tick"><span class="num">Step ${n}</span> ${inline(step.title)}</label>`);
  parts.push(`<button type="button" class="why-btn" aria-describedby="${id}-why">Why?</button>`);
  parts.push(`<div class="why" role="tooltip" id="${id}-why"><span class="why-label">Why we do this</span>${paragraphs(step.why)}</div>`);
  parts.push('</div>');
  parts.push('<div class="step-body">');
  if (step.warning) {
    parts.push(`<div class="warning"><span class="tag">Careful</span>${paragraphs(step.warning)}</div>`);
  }
  parts.push(`<div class="do">${paragraphs(step.do)}</div>`);
  if (step.paste) {
    parts.push('<div class="paste">');
    parts.push(`<p class="paste-into" id="${id}-into">Copy this, then paste it into <strong>${esc(step.paste.into)}</strong>:</p>`);
    parts.push(`<pre class="paste-text" id="${id}-paste" tabindex="0" aria-labelledby="${id}-into">${esc(step.paste.text)}</pre>`);
    parts.push(`<button type="button" class="copy-btn" data-copy="${id}-paste" aria-label="Copy the text for step ${n}">Copy</button>`);
    parts.push('</div>');
  }
  if (step.expect) {
    parts.push(`<div class="expect"><span class="tag">You should see</span>${paragraphs(step.expect)}</div>`);
  }
  if (step.stuck) {
    parts.push(`<div class="if-stuck"><span class="tag">If that does not happen</span>${paragraphs(step.stuck)}</div>`);
  }
  parts.push(`<button type="button" class="stuck-btn" aria-label="I am stuck on step ${n}: copy a message to send to Claude">I'm stuck on this step</button>`);
  parts.push('</div>');
  parts.push('</li>');
  return parts.join('\n');
}

function renderSteps(steps) {
  const out = [];
  let open = false;
  let group = null;
  steps.forEach((step, i) => {
    if (!open || step.group !== group) {
      if (open) out.push('</ol>');
      group = step.group;
      if (group) out.push(`<h2 class="group">${esc(group)}</h2>`);
      out.push(`<ol class="steps" start="${i + 1}">`);
      open = true;
    }
    out.push(renderStep(step, i));
  });
  out.push('</ol>');
  return out.join('\n');
}

function readAsset(name) {
  // normalise newlines so a CRLF checkout produces the same page (and the same CSP hash)
  return fs.readFileSync(path.join(ASSETS, name), 'utf8').replace(/\r\n/g, '\n');
}

function cspHash(content) {
  return `'sha256-${createHash('sha256').update(content, 'utf8').digest('base64')}'`;
}

/** Build the whole page. `slug` names the browser-storage slot that remembers the ticks. */
export function renderHtml(checklist, slug) {
  const css = `\n${readAsset('checklist.css')}\n`;
  const js = `\n${readAsset('checklist.js')}\n`;
  const csp = [
    "default-src 'none'",
    `style-src ${cspHash(css)}`,
    `script-src ${cspHash(js)}`,
    "base-uri 'none'",
    "form-action 'none'",
  ].join('; ');

  const total = checklist.steps.length;
  const head = [];
  if (checklist.source) {
    const label = esc(checklist.source);
    head.push(`<p class="source">${checklist.sourceUrl
      ? `<a href="${esc(checklist.sourceUrl)}" target="_blank" rel="noopener noreferrer">${label}</a>`
      : label}</p>`);
  }
  head.push(`<h1>${esc(checklist.title)}</h1>`);
  head.push(`<div class="summary">${paragraphs(checklist.summary)}</div>`);
  const facts = [`${total} ${total === 1 ? 'step' : 'steps'}`];
  if (checklist.minutes) facts.push(`about ${checklist.minutes} ${checklist.minutes === 1 ? 'minute' : 'minutes'}`);
  head.push(`<p class="facts">${facts.join(' · ')}</p>`);

  const extras = [];
  if (checklist.before.length) {
    extras.push('<section class="card" aria-labelledby="before-h"><h2 id="before-h">Have these ready first</h2><ul>');
    for (const item of checklist.before) extras.push(`<li>${inline(item)}</li>`);
    extras.push('</ul></section>');
  }
  if (checklist.words.length) {
    extras.push('<details class="card words"><summary>Words you will see (click to open)</summary><dl>');
    for (const w of checklist.words) extras.push(`<dt>${esc(w.word)}</dt><dd>${inline(w.meaning)}</dd>`);
    extras.push('</dl></details>');
  }

  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="${esc(csp)}">
<meta name="referrer" content="no-referrer">
<title>${esc(checklist.title)}</title>
<style>${css}</style>
</head>
<body data-slug="${esc(slug)}" data-title="${esc(checklist.title)}">
<header class="top">
${head.join('\n')}
</header>
<div class="progress-row">
<label for="progress">Your progress</label>
<progress id="progress" value="0" max="${total}"></progress>
<span id="progress-text" aria-live="polite">0 of ${total} done</span>
<button type="button" class="save-btn" id="save-btn">Save my progress</button>
</div>
<main>
<p class="how">Do one step at a time, top to bottom, and tick each box when it is done. Point at a step (or press its <strong>Why?</strong> button) to see why we do it. If a step does not go the way it says, press <strong>I'm stuck on this step</strong>.</p>
<p class="how">You do not have to finish in one sitting. Press <strong>Save my progress</strong>, close this page, and when you are ready type <code>/help-me continue</code> in Claude to open it again with your ticks in place.</p>
<noscript><p class="how">Ticks and the copy buttons need JavaScript. You can still read and follow every step.</p></noscript>
${extras.join('\n')}
${renderSteps(checklist.steps)}
<section class="done" id="done" hidden aria-labelledby="done-h">
<h2 id="done-h">All done</h2>
<p>Every step is ticked. Let Claude know, so it can check the result with you.</p>
<button type="button" class="copy-btn" id="done-btn">Copy a message for Claude</button>
</section>
<p class="foot"><button type="button" class="link-btn" id="reset-btn">Untick everything and start again</button></p>
</main>
<div class="toast" id="toast" role="status" aria-live="polite"></div>
<script>${js}</script>
</body>
</html>
`;
}

/* ------------------------------------------------------------- build page */

export function slugOf(filePath) {
  const base = path.basename(filePath, path.extname(filePath));
  return base.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'checklist';
}

function readChecklist(jsonPath) {
  let raw;
  try {
    raw = JSON.parse(fs.readFileSync(jsonPath, 'utf8').replace(/^﻿/, ''));
  } catch (err) {
    if (err.code === 'ENOENT') throw new ChecklistError(`no such file: ${jsonPath}`);
    if (err instanceof SyntaxError) throw new ChecklistError(`${jsonPath} is not valid JSON: ${err.message}`);
    throw err;
  }
  return validateChecklist(raw);
}

/** Write the page for one checklist file. Without `outPath` it lands beside the JSON. */
export function build(jsonPath, outPath = null) {
  const checklist = readChecklist(jsonPath);
  const out = path.resolve(outPath || path.join(path.dirname(jsonPath), `${slugOf(jsonPath)}.html`));
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out, renderHtml(checklist, slugOf(out)), 'utf8');
  return { out, steps: checklist.steps.length };
}

/* ------------------------------------------------------------------ store */
/* Checklists are kept in one folder in the person's home directory, so they
   outlive the conversation that made them. A checklist is "open" while its
   JSON sits in that folder; finishing it moves it into done/. */

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

/** The folder open checklists live in. HELP_ME_HOME overrides the default. */
export function storeDir(env = process.env) {
  if (Object.hasOwn(env, 'HELP_ME_HOME')) {
    const value = String(env.HELP_ME_HOME).trim();
    if (!value) throw new ChecklistError('HELP_ME_HOME is set but empty');
    return path.resolve(value);
  }
  return path.join(os.homedir(), '.help-me');
}

function checkSlug(slug) {
  if (typeof slug !== 'string' || !SLUG_RE.test(slug)) {
    throw new ChecklistError(`"${slug}" is not a checklist name (use the slug that --list prints)`);
  }
  return slug;
}

/** The one place a timestamp is turned into text. */
function isoTime(date) {
  return date.toISOString();
}

function sameFile(a, b) {
  try {
    return fs.realpathSync.native(a) === fs.realpathSync.native(b);
  } catch {
    return false; // one of them does not exist yet
  }
}

/** Keep a checklist: copy its JSON into the store and write its page there. */
export function store(jsonPath, dir = storeDir()) {
  const checklist = readChecklist(jsonPath);
  const slug = slugOf(jsonPath);
  fs.mkdirSync(dir, { recursive: true });
  const json = path.join(dir, `${slug}.json`);
  if (!sameFile(jsonPath, json)) fs.copyFileSync(jsonPath, json);
  const out = path.join(dir, `${slug}.html`);
  fs.writeFileSync(out, renderHtml(checklist, slug), 'utf8');
  return { slug, out, json, steps: checklist.steps.length };
}

/** Every open checklist, the most recently saved first. */
export function listOpen(dir = storeDir()) {
  let names;
  try {
    names = fs.readdirSync(dir);
  } catch (err) {
    if (err.code === 'ENOENT') return [];
    throw err;
  }
  const items = [];
  for (const name of names) {
    if (path.extname(name) !== '.json') continue;
    const slug = path.basename(name, '.json');
    if (!SLUG_RE.test(slug)) continue;
    const json = path.join(dir, name);
    const item = { slug, saved: isoTime(fs.statSync(json).mtime), json, page: path.join(dir, `${slug}.html`) };
    try {
      const checklist = readChecklist(json);
      item.title = checklist.title;
      item.source = checklist.source;
      item.steps = checklist.steps.length;
    } catch (err) {
      if (!(err instanceof ChecklistError)) throw err;
      item.problem = err.message;
    }
    items.push(item);
  }
  return items.sort((a, b) => (a.saved < b.saved ? 1 : a.saved > b.saved ? -1 : a.slug.localeCompare(b.slug)));
}

function storedJson(slug, dir) {
  const json = path.join(dir, `${checkSlug(slug)}.json`);
  if (!fs.existsSync(json)) throw new ChecklistError(`there is no open checklist called "${slug}"`);
  return json;
}

/** Rebuild the page of an open checklist, so it picks up the current page code. Returns what store returns. */
export function reopen(slug, dir = storeDir()) {
  return store(storedJson(slug, dir), dir);
}

/** Mark a checklist finished: it leaves the open list and is kept in done/. */
export function finish(slug, dir = storeDir()) {
  const json = storedJson(slug, dir);
  const doneDir = path.join(dir, 'done');
  fs.mkdirSync(doneDir, { recursive: true });
  fs.renameSync(json, path.join(doneDir, `${slug}.json`));
  const page = path.join(dir, `${slug}.html`);
  if (fs.existsSync(page)) fs.renameSync(page, path.join(doneDir, `${slug}.html`));
  return { slug, dir: doneDir };
}

/* ------------------------------------------------------------------- main */

function openInBrowser(file) {
  // each of these takes the path as one argument, so no shell ever parses it
  const cmd = process.platform === 'win32' ? ['explorer.exe', [file]]
    : process.platform === 'darwin' ? ['open', [file]]
      : ['xdg-open', [file]];
  return new Promise((resolve) => {
    try {
      const child = spawn(cmd[0], cmd[1], { detached: true, stdio: 'ignore' });
      child.once('error', () => resolve(false));
      child.once('spawn', () => { child.unref(); resolve(true); });
    } catch {
      resolve(false);
    }
  });
}

const USAGE = `usage:
  node build-checklist.mjs <checklist.json> [--no-open] [-q]   keep the checklist and open its page
  node build-checklist.mjs <checklist.json> -o <out.html>      write the page there instead, keeping nothing
  node build-checklist.mjs --list                              print the open checklists as JSON
  node build-checklist.mjs --open <slug> [--no-open]           reopen an open checklist
  node build-checklist.mjs --done <slug>                       mark a checklist finished`;

const VALUE_FLAGS = { '-o': 'out', '--out': 'out', '--open': 'open', '--done': 'done' };
const SWITCHES = { '-q': 'quiet', '--quiet': 'quiet', '--no-open': 'noOpen', '--list': 'list', '-h': 'help', '--help': 'help' };

export function parseArgs(args) {
  const opts = { inputs: [] };
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (Object.hasOwn(VALUE_FLAGS, arg)) {
      const value = args[i + 1];
      if (value === undefined || value.startsWith('-')) throw new ChecklistError(`${arg} needs a value`);
      opts[VALUE_FLAGS[arg]] = value;
      i++;
    } else if (Object.hasOwn(SWITCHES, arg)) opts[SWITCHES[arg]] = true;
    else if (arg.startsWith('-')) throw new ChecklistError(`unknown option ${arg}`);
    else opts.inputs.push(arg);
  }
  const modes = [opts.list, opts.open, opts.done, opts.inputs.length > 0].filter(Boolean).length;
  if (!opts.help && modes !== 1) throw new ChecklistError('give one checklist file, or one of --list, --open, --done');
  if (opts.inputs.length > 1) throw new ChecklistError('give one checklist file at a time');
  return opts;
}

async function show(result, opts) {
  if (!opts.quiet) console.log(`wrote ${result.out}  (${result.steps} ${result.steps === 1 ? 'step' : 'steps'})`);
  if (opts.noOpen) return;
  const opened = await openInBrowser(result.out);
  if (!opts.quiet) {
    console.log(opened
      ? 'opened it in the web browser'
      : 'could not open the web browser: open that file by hand');
  }
}

async function main(argv) {
  try {
    const opts = parseArgs(argv.slice(2));
    if (opts.help) { console.log(USAGE); return 0; }
    if (opts.list) { console.log(JSON.stringify(listOpen(), null, 2)); return 0; }
    if (opts.done) {
      const done = finish(opts.done);
      if (!opts.quiet) console.log(`finished ${done.slug}: moved to ${done.dir}`);
      return 0;
    }
    if (opts.open) { await show(reopen(opts.open), opts); return 0; }
    await show(opts.out ? build(opts.inputs[0], opts.out) : store(opts.inputs[0]), opts);
    return 0;
  } catch (err) {
    if (err instanceof ChecklistError) { console.error(`Checklist problem: ${err.message}\n${USAGE}`); return 2; }
    throw err;
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main(process.argv).then((code) => { process.exitCode = code; });
}
