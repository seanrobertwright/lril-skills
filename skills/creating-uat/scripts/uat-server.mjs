#!/usr/bin/env node
/**
 * Local helper for filling in a UAT.
 *
 *     node uat-server.mjs path/to/UAT-myapp-2026-08-23.md
 *
 * Regenerates the HTML form, serves it at http://localhost:8777, and:
 *   * Save        -> writes .uat-progress-<slug>.json so nothing is ever lost
 *   * screenshots -> saved into assets/<slug>/ and linked from the markdown
 *   * Submit      -> validates, then writes the answers back into the markdown
 *                    and drops a machine-readable <name>.results.json
 *
 * No dependencies. Binds to 127.0.0.1 (this computer only). Stop it with Ctrl+C.
 * Mirrors uat_server.py exactly.
 */

import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { parse, generate, ID_RE, UatError } from './generate-uat-html.mjs';

const MAX_UPLOAD = 8 * 1024 * 1024;
const MAX_BODY = 24 * 1024 * 1024;
const EXT_BY_MIME = {
  'image/png': '.png', 'image/jpeg': '.jpg', 'image/gif': '.gif',
  'image/webp': '.webp', 'image/avif': '.avif',
};
const MIME_BY_EXT = {
  '.html': 'text/html; charset=utf-8', '.png': 'image/png', '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg', '.gif': 'image/gif', '.webp': 'image/webp', '.avif': 'image/avif',
  '.json': 'application/json; charset=utf-8', '.md': 'text/markdown; charset=utf-8',
};
const STATUS_MD = { pass: ['x', 'PASS'], fail: ['!', 'FAIL'], notdone: ['~', 'NOT DONE'] };
const SEV_LABEL = { cosmetic: 'Cosmetic', annoying: 'Annoying', blocker: 'Blocks me' };

class Ctx {
  constructor(mdPath) {
    this.mdPath = path.resolve(mdPath);
    this.dir = path.dirname(this.mdPath);
    this.slug = path.basename(this.mdPath, path.extname(this.mdPath));
    this.htmlPath = path.join(this.dir, this.slug + '.html');
    this.progressPath = path.join(this.dir, `.uat-progress-${this.slug}.json`);
    this.resultsPath = path.join(this.dir, this.slug + '.results.json');
    this.assetsDir = path.join(this.dir, 'assets', this.slug);
  }

  loadMd() {
    return fs.readFileSync(this.mdPath, 'utf8').replace(/\r\n/g, '\n').split('\n');
  }

  index() {
    const lines = this.loadMd();
    const { meta, sections, spans } = parse(lines);
    const info = {};
    for (const s of sections) for (const t of s.tests) info[t.id] = { title: t.title, section: s.id };
    return { lines, meta, sections, spans, info };
  }
}

/* -------------------------------------------------------------- validation */

function validate(state, info, partial) {
  const problems = [];
  if (!(state.tester || '').trim()) problems.push({ id: null, msg: 'No tester name was filled in.' });
  const answers = state.answers || {};
  for (const tid of Object.keys(info)) {
    const a = answers[tid] || {};
    const status = (a.status || '').trim();
    const notes = (a.notes || '').trim();
    const concern = (a.concern || '').trim();
    if (!status) {
      if (!partial) problems.push({ id: tid, msg: `Test ${tid} has no answer yet.` });
      continue;
    }
    if (!STATUS_MD[status]) {
      problems.push({ id: tid, msg: `Test ${tid} has an unknown status "${status}".` });
      continue;
    }
    if ((status === 'fail' || status === 'notdone') && notes.length < 10) {
      problems.push({ id: tid, msg: `Test ${tid} is marked ${STATUS_MD[status][1]} but has no explanation.` });
    }
    if (concern && !(a.severity || '').trim()) {
      problems.push({ id: tid, msg: `Test ${tid} has a look-and-feel comment with no severity.` });
    }
  }
  for (const f of state.findings || []) {
    const fid = f.id || '?';
    if (!(f.title || '').trim()) problems.push({ id: fid, msg: `Finding ${fid} has no title.` });
    if (!(f.description || '').trim()) problems.push({ id: fid, msg: `Finding ${fid} has no description.` });
    if (!(f.severity || '').trim()) problems.push({ id: fid, msg: `Finding ${fid} has no severity.` });
  }
  return problems;
}

function countsOf(state, info) {
  const c = { pass: 0, fail: 0, notdone: 0, unanswered: 0, concerns: 0, findings: (state.findings || []).length };
  const answers = state.answers || {};
  for (const tid of Object.keys(info)) {
    const a = answers[tid] || {};
    const st = a.status || '';
    c[STATUS_MD[st] ? st : 'unanswered']++;
    if ((a.concern || '').trim()) c.concerns++;
  }
  return c;
}

/* --------------------------------------------------------- markdown writing */

function shotLines(owner, shots) {
  const out = [];
  (shots || []).forEach((s, i) => {
    const p = typeof s === 'string' ? s : s && s.path;
    if (!p || p.startsWith('data:')) return;
    out.push(`  - ![${owner} screenshot ${i + 1}](${p})`);
  });
  return out;
}

function answerMd(tid, a) {
  a = a || {};
  const status = a.status || '';
  const notes = (a.notes || '').trim();
  const concern = (a.concern || '').trim();
  const sev = SEV_LABEL[(a.severity || '').trim()] || '';
  const lines = [];
  lines.push(STATUS_MD[status]
    ? `- [${STATUS_MD[status][0]}] **Status:** ${STATUS_MD[status][1]}`
    : '- [ ] **Status:** _not answered_');
  lines.push('- **Notes:** ' + (notes ? notes.replace(/\n/g, '\n  ') : '_none_'));
  lines.push(concern
    ? `- **Look & feel concern:** (${sev || 'unrated'}) ${concern.replace(/\n/g, '\n  ')}`
    : '- **Look & feel concern:** _none_');
  const shots = shotLines(tid, a.screenshots);
  lines.push('- **Screenshots:**' + (shots.length ? '' : ' _none_'));
  return lines.concat(shots);
}

function natural(s) {
  return String(s).split(/(\d+)/).map((p) => (/^\d+$/.test(p) ? p.padStart(9, '0') : p)).join('');
}
const byNatural = (a, b) => (natural(a) < natural(b) ? -1 : natural(a) > natural(b) ? 1 : 0);

function summaryMd(state, info, counts, partial, when) {
  const tester = (state.tester || '').trim() || 'unnamed tester';
  const answers = state.answers || {};
  const ids = Object.keys(info);
  const failed = ids.filter((t) => (answers[t] || {}).status === 'fail').sort(byNatural);
  const notdone = ids.filter((t) => (answers[t] || {}).status === 'notdone').sort(byNatural);
  const concerned = ids.filter((t) => ((answers[t] || {}).concern || '').trim()).sort(byNatural);
  const unanswered = ids.filter((t) => !(answers[t] || {}).status).sort(byNatural);
  const total = ids.length;
  const lines = [
    `> **Run status:** ${partial ? 'PARTIAL (unfinished)' : 'COMPLETE'} — submitted ${when} by ${tester}`,
    `> **Result:** ${counts.pass} of ${total} passed · ${counts.fail} failed · ${counts.notdone} not done · `
      + `${counts.concerns} look-and-feel concerns · ${counts.findings} other findings`,
    '>',
    '> | Status | Count |',
    '> |---|---|',
    `> | Pass | ${counts.pass} |`,
    `> | Fail | ${counts.fail} |`,
    `> | Not done | ${counts.notdone} |`,
    `> | Unanswered | ${counts.unanswered} |`,
    '>',
  ];
  lines.push('> **Failed tests:** ' + (failed.length ? failed.join(', ') : 'none'));
  if (notdone.length) lines.push('> **Not done:** ' + notdone.join(', '));
  lines.push('> **Tests with look-and-feel concerns:** ' + (concerned.length ? concerned.join(', ') : 'none'));
  if (unanswered.length) lines.push('> **Never answered:** ' + unanswered.join(', '));
  return lines;
}

function findingsMd(state) {
  const fs_ = state.findings || [];
  const head = ['## Anything else the tester noticed', ''];
  if (!fs_.length) return head.concat(['_No tester-reported findings._']);
  const out = head.slice();
  for (const f of fs_) {
    const fid = f.id || 'F?';
    out.push(`### ${fid} — ${(f.title || '').trim() || '(no title)'}`);
    const sec = (f.section || '').trim();
    out.push('- **Reported from:** ' + (sec ? `Section ${sec}` : 'the end of the checklist'));
    out.push('- **Severity:** ' + (SEV_LABEL[(f.severity || '').trim()] || 'unrated'));
    out.push('- **What happened:** ' + (f.description || '').trim().replace(/\n/g, '\n  '));
    const shots = shotLines(fid, f.screenshots);
    out.push('- **Screenshots:**' + (shots.length ? '' : ' _none_'));
    out.push(...shots);
    out.push('');
  }
  out.pop();
  return out;
}

function stamp() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

function writeMarkdown(ctx, state, partial) {
  const { lines, spans, info } = ctx.index();
  const counts = countsOf(state, info);
  const when = stamp();
  const answers = state.answers || {};

  const edits = [];
  for (const [tid, span] of Object.entries(spans.answers)) {
    edits.push([span[0] + 1, span[1] - 1, answerMd(tid, answers[tid])]);
  }
  if (spans.summary) edits.push([spans.summary[0] + 1, spans.summary[1] - 1, summaryMd(state, info, counts, partial, when)]);
  if (spans.findings) edits.push([spans.findings[0] + 1, spans.findings[1] - 1, findingsMd(state)]);

  edits.sort((a, b) => b[0] - a[0]);
  for (const [start, end, repl] of edits) lines.splice(start, end - start + 1, ...repl);

  if (spans.meta) {
    const [ms, me] = spans.meta;
    let block = lines.slice(ms, me + 1).filter((l) => !/^\s*(tester:|last_run:)/.test(l));
    block = block.slice(0, -1)
      .concat([`tester: ${(state.tester || '').trim()}`, `last_run: ${when}`])
      .concat(block.slice(-1));
    lines.splice(ms, me - ms + 1, ...block);
  }

  fs.writeFileSync(ctx.mdPath, lines.join('\n'), 'utf8');

  const results = {
    uat: path.basename(ctx.mdPath),
    tester: (state.tester || '').trim(),
    submitted: new Date().toISOString().slice(0, 19),
    partial: Boolean(partial),
    counts,
    answers: {},
    findings: state.findings || [],
  };
  for (const [tid, m] of Object.entries(info)) {
    const a = answers[tid] || {};
    results.answers[tid] = {
      status: a.status || 'unanswered',
      title: m.title,
      section: m.section,
      notes: (a.notes || '').trim(),
      concern: (a.concern || '').trim(),
      severity: (a.severity || '').trim(),
      screenshots: (a.screenshots || [])
        .filter((s) => s && typeof s.path === 'string' && s.path.startsWith('assets/'))
        .map((s) => s.path),
    };
  }
  fs.writeFileSync(ctx.resultsPath, JSON.stringify(results, null, 2), 'utf8');
  return counts;
}

/* ------------------------------------------------------------------ server */

function sendJson(res, obj, code = 200) {
  const body = Buffer.from(JSON.stringify(obj), 'utf8');
  res.writeHead(code, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': body.length,
    'Cache-Control': 'no-store',
  });
  res.end(body);
}

function readJson(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    req.on('data', (c) => {
      size += c.length;
      if (size > MAX_BODY) { reject(new Error('request body too large')); req.destroy(); return; }
      chunks.push(c);
    });
    req.on('end', () => {
      try { resolve(JSON.parse(Buffer.concat(chunks).toString('utf8'))); }
      catch (e) { reject(e); }
    });
    req.on('error', reject);
  });
}

function safePath(ctx, urlPath) {
  const rel = decodeURIComponent(urlPath).replace(/^\/+/, '');
  if (!rel) return ctx.htmlPath;
  const full = path.resolve(ctx.dir, rel);
  const base = ctx.dir.endsWith(path.sep) ? ctx.dir : ctx.dir + path.sep;
  if (!full.startsWith(base)) return null;
  return full;
}

function handleUpload(ctx, payload, res) {
  const owner = String(payload.owner || '').trim();
  if (!owner || !ID_RE.test(owner)) return sendJson(res, { error: 'bad owner id' }, 400);
  const m = /^data:([\w/+.-]+);base64,([\s\S]*)$/.exec(payload.dataUrl || '');
  if (!m) return sendJson(res, { error: 'that file was not an image' }, 400);
  const [, mime, b64] = m;
  const ext = EXT_BY_MIME[mime];
  if (!ext) return sendJson(res, { error: `unsupported image type ${mime}` }, 400);
  let raw;
  try { raw = Buffer.from(b64, 'base64'); } catch { return sendJson(res, { error: 'the image could not be decoded' }, 400); }
  if (!raw.length) return sendJson(res, { error: 'the image could not be decoded' }, 400);
  if (raw.length > MAX_UPLOAD) return sendJson(res, { error: 'that image is larger than 8 MB' }, 400);
  fs.mkdirSync(ctx.assetsDir, { recursive: true });
  let n = 1;
  while (fs.existsSync(path.join(ctx.assetsDir, `${owner}-${n}${ext}`))) n++;
  const name = `${owner}-${n}${ext}`;
  fs.writeFileSync(path.join(ctx.assetsDir, name), raw);
  const rel = `assets/${ctx.slug}/${name}`;
  console.log(`  saved screenshot ${rel} (${Math.round(raw.length / 1024)} KB)`);
  return sendJson(res, { ok: true, path: rel });
}

function handleSubmit(ctx, payload, res) {
  const state = payload.state || {};
  const partial = Boolean(payload.partial);
  let info;
  try { ({ info } = ctx.index()); }
  catch (err) { return sendJson(res, { error: `the checklist file has a problem: ${err.message}` }, 500); }

  const problems = validate(state, info, partial);
  if (problems.length) return sendJson(res, { ok: false, error: 'Some answers are missing.', problems });

  state.updatedAt = Date.now();
  fs.writeFileSync(ctx.progressPath, JSON.stringify(state, null, 2), 'utf8');

  let counts;
  try { counts = writeMarkdown(ctx, state, partial); }
  catch (err) { return sendJson(res, { error: `could not write the checklist: ${err.message}` }, 500); }

  try { generate(ctx.mdPath, ctx.htmlPath, true); } catch { /* the markdown is already written */ }

  let summary = `${counts.pass} passed, ${counts.fail} failed, ${counts.notdone} not done, `
    + `${counts.concerns} look-and-feel concerns, ${counts.findings} other findings.`;
  if (partial) summary += ` ${counts.unanswered} test(s) were left unanswered — the report is marked as unfinished.`;
  console.log(`\n  SUBMITTED — ${summary}`);
  console.log(`  wrote ${ctx.mdPath}`);
  console.log(`  wrote ${ctx.resultsPath}\n`);
  return sendJson(res, {
    ok: true, partial, summary,
    mdPath: ctx.mdPath,
    mdRel: path.basename(ctx.mdPath),
    results: ctx.resultsPath,
  });
}

function makeServer(ctx) {
  return http.createServer(async (req, res) => {
    const urlPath = (req.url || '/').split('?')[0];
    try {
      if (req.method === 'GET') {
        if (urlPath === '/api/state') {
          let state = {};
          if (fs.existsSync(ctx.progressPath)) {
            try { state = JSON.parse(fs.readFileSync(ctx.progressPath, 'utf8')); } catch { state = {}; }
          }
          return sendJson(res, { state });
        }
        const full = safePath(ctx, urlPath);
        if (!full || !fs.existsSync(full) || !fs.statSync(full).isFile()) {
          return sendJson(res, { error: 'not found' }, 404);
        }
        const data = fs.readFileSync(full);
        res.writeHead(200, {
          'Content-Type': MIME_BY_EXT[path.extname(full).toLowerCase()] || 'application/octet-stream',
          'Content-Length': data.length,
          'Cache-Control': 'no-store',
        });
        return res.end(data);
      }

      if (req.method === 'POST') {
        let payload;
        try { payload = await readJson(req); }
        catch (err) { return sendJson(res, { error: `bad request: ${err.message}` }, 400); }

        if (urlPath === '/api/save') {
          const state = payload.state || {};
          state.updatedAt = Date.now();
          fs.writeFileSync(ctx.progressPath, JSON.stringify(state, null, 2), 'utf8');
          console.log(`  saved progress (${Object.keys(state.answers || {}).length} answers)`);
          return sendJson(res, { ok: true });
        }
        if (urlPath === '/api/upload') return handleUpload(ctx, payload, res);
        if (urlPath === '/api/submit') return handleSubmit(ctx, payload, res);
      }
      return sendJson(res, { error: 'unknown endpoint' }, 404);
    } catch (err) {
      return sendJson(res, { error: String(err && err.message || err) }, 500);
    }
  });
}

function listen(server, port, attempt = 0) {
  return new Promise((resolve, reject) => {
    const onError = (err) => {
      if (err.code === 'EADDRINUSE' && attempt < 19) {
        server.removeListener('error', onError);
        resolve(listen(server, port + 1, attempt + 1));
      } else reject(err);
    };
    server.once('error', onError);
    server.listen(port, '127.0.0.1', () => {
      server.removeListener('error', onError);
      resolve(port);
    });
  });
}

function openBrowser(url) {
  const cmd = process.platform === 'win32' ? ['cmd', ['/c', 'start', '', url]]
    : process.platform === 'darwin' ? ['open', [url]]
      : ['xdg-open', [url]];
  try { spawn(cmd[0], cmd[1], { detached: true, stdio: 'ignore' }).unref(); } catch { /* not important */ }
}

async function main(argv) {
  const args = argv.slice(2);
  if (!args.length || args.includes('-h') || args.includes('--help')) {
    console.log('usage: node uat-server.mjs <UAT.md> [-p PORT] [--no-browser]');
    return args.length ? 0 : 2;
  }
  const pi = Math.max(args.indexOf('-p'), args.indexOf('--port'));
  const port = pi > -1 ? Number(args[pi + 1]) : 8777;
  const noBrowser = args.includes('--no-browser');
  const md = args.find((a, i) => !a.startsWith('-') && (pi === -1 || i !== pi + 1));

  if (!md || !fs.existsSync(md)) { console.error(`No such file: ${md}`); return 2; }
  const ctx = new Ctx(md);
  try { generate(ctx.mdPath, ctx.htmlPath, true); }
  catch (err) {
    if (err instanceof UatError) { console.error(`UAT file problem: ${err.message}`); return 2; }
    throw err;
  }

  const server = makeServer(ctx);
  const actual = await listen(server, port);
  const url = `http://localhost:${actual}/`;
  console.log('');
  console.log('  UAT helper is running.');
  console.log(`  Checklist : ${ctx.mdPath}`);
  console.log(`  Open this in your web browser:  ${url}`);
  console.log('  Leave this window open while you work. Press Ctrl+C here when you are finished.');
  console.log('');
  if (!noBrowser) setTimeout(() => openBrowser(url), 600);
  process.on('SIGINT', () => {
    console.log(`\n  Stopped. Your answers are in ${ctx.progressPath}`);
    process.exit(0);
  });
  return 0;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main(process.argv).then((code) => { if (code) process.exit(code); });
}
