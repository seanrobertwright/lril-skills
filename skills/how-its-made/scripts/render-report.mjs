#!/usr/bin/env node
/**
 * Render a how-its-made report from its JSON source.
 *
 *     node render-report.mjs how-its-made/owner-repo-2026-11-05.json
 *
 * Writes the .md and .html files beside the input. No dependencies.
 * The JSON shape and its rules are documented in ../references/report-schema.md.
 *
 * Everything in the report may quote a hostile repository, so all values pass
 * through esc() or mdText(), links pass through safeHref(), and the page carries
 * a CSP that permits only its own hashed stylesheet. The page has no JavaScript.
 */

import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

export const LABELS = ['Enforced', 'Used', 'Present'];
export const STAGES = ['spec', 'plan', 'code', 'test', 'review', 'merge', 'release'];
export const CATEGORIES = ['method', 'framework', 'agent', 'skill', 'mcp', 'review', 'ci', 'other'];
export const COVERAGE = ['Covered', 'Partial', 'Gap'];
export const RELATIONSHIPS = ['original', 'fork', 'template', 'mirror'];
export const MIN_DIAGRAM_STAGES = 2;

const MAX_PER_ROW = 5;
const MAX_TOOL_CHARS = 20;
const EMAIL_RE = /[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}/;
const SHA_RE = /^[0-9a-f]{40}$/;
const OWNER_RE = /^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$/;
const REPO_RE = /^[A-Za-z0-9._-]{1,100}$/;
// Control characters and bidi overrides, which can disguise quoted text.
const UNSAFE_CHARS_RE = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F‪-‮⁦-⁩]/g;

/* ------------------------------ text safety ------------------------------ */

export function esc(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

/** Escape text for Markdown so quoted repo content cannot inject markup or raw HTML. */
export function mdText(value) {
  return String(value ?? '')
    .replace(/\s*\r?\n\s*/g, ' ')
    .replace(/[\\`*_[\]<>|~#]/g, (c) => `\\${c}`);
}

/** Return a normalised http(s) URL, or null for anything else. */
export function safeHref(url) {
  if (typeof url !== 'string') return null;
  let parsed;
  try {
    parsed = new URL(url);
  } catch {
    return null;
  }
  return parsed.protocol === 'http:' || parsed.protocol === 'https:' ? parsed.href : null;
}

/** Shorten by code point so a truncation never splits a surrogate pair. */
export function truncate(value, max) {
  const chars = [...String(value ?? '')];
  return chars.length <= max ? chars.join('') : `${chars.slice(0, max - 1).join('')}…`;
}

function isRealDate(value) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(value));
  if (!match) return false;
  const [year, month, day] = match.slice(1).map(Number);
  if (month < 1 || month > 12 || day < 1) return false;
  const leap = (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0;
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  return day <= days[month - 1];
}

/** Strip unsafe characters from every string in the report, returning a copy. */
function scrub(value) {
  if (typeof value === 'string') return value.replace(UNSAFE_CHARS_RE, '');
  if (Array.isArray(value)) return value.map(scrub);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, scrub(v)]));
  }
  return value;
}

function findEmails(value, at, problems) {
  if (typeof value === 'string') {
    if (EMAIL_RE.test(value)) problems.push(`${at}: contains an email address; reports never include emails`);
  } else if (Array.isArray(value)) {
    value.forEach((item, i) => findEmails(item, `${at}[${i}]`, problems));
  } else if (value && typeof value === 'object') {
    for (const [k, v] of Object.entries(value)) findEmails(v, `${at}.${k}`, problems);
  }
}

/* ------------------------------- validation ------------------------------ */

/**
 * Check a parsed report against the schema and the evidence rules.
 * Returns { report, problems }; report is usable only when problems is empty.
 */
export function validateReport(input) {
  const problems = [];
  if (!input || typeof input !== 'object' || Array.isArray(input)) {
    return { report: null, problems: ['report: must be a JSON object'] };
  }
  const report = scrub(input);

  const text = (value, at) => {
    if (typeof value !== 'string' || value.trim() === '') problems.push(`${at}: must be a non-empty string`);
  };
  const list = (value, at) => {
    if (!Array.isArray(value)) {
      problems.push(`${at}: must be an array`);
      return [];
    }
    return value;
  };
  const oneOf = (value, allowed, at) => {
    if (!allowed.includes(value)) problems.push(`${at}: must be one of ${allowed.join(', ')}`);
  };
  const citations = (value, at) => {
    const items = list(value, at);
    if (Array.isArray(value) && items.length === 0) problems.push(`${at}: needs at least one citation`);
    items.forEach((c, i) => text(c?.text, `${at}[${i}].text`));
  };
  const date = (value, at) => {
    if (!isRealDate(value)) problems.push(`${at}: must be a real YYYY-MM-DD date`);
  };

  const repo = report.repo ?? {};
  if (!OWNER_RE.test(repo.owner ?? '')) problems.push('repo.owner: not a valid GitHub owner');
  if (!REPO_RE.test(repo.name ?? '') || repo.name === '.' || repo.name === '..') {
    problems.push('repo.name: not a valid GitHub repository name');
  }
  if (!SHA_RE.test(repo.sha ?? '')) problems.push('repo.sha: must be the full 40-character commit SHA');
  date(repo.analyzedAt, 'repo.analyzedAt');
  oneOf(repo.visibility, ['public', 'private'], 'repo.visibility');
  oneOf(repo.relationship, RELATIONSHIPS, 'repo.relationship');
  if (repo.subpath !== undefined) text(repo.subpath, 'repo.subpath');
  if (repo.noDivergence === true && !safeHref(repo.upstream)) {
    problems.push('repo.upstream: an http(s) URL is required when repo.noDivergence is true');
  }

  text(report.summary, 'summary');
  list(report.narrative, 'narrative').forEach((p, i) => text(p, `narrative[${i}]`));

  const history = report.history ?? {};
  oneOf(history.quality, ['full', 'thin'], 'history.quality');
  const coverage = report.coverage ?? {};
  oneOf(coverage.gh, ['available', 'unavailable', 'rate-limited'], 'coverage.gh');
  for (const key of ['commitsScanned', 'prsSampled', 'prsTotal']) {
    if (!Number.isInteger(coverage[key]) || coverage[key] < 0) {
      problems.push(`coverage.${key}: must be a non-negative integer`);
    }
  }
  const limitations = list(report.limitations, 'limitations');
  limitations.forEach((l, i) => text(l, `limitations[${i}]`));
  if (limitations.length === 0 && (history.quality === 'thin' || coverage.gh !== 'available')) {
    problems.push('limitations: must explain what could not be determined when history is thin or gh evidence is missing');
  }

  const thin = history.quality === 'thin';
  const label = (value, at) => {
    oneOf(value, LABELS, at);
    if (thin && value === 'Used') problems.push(`${at}: Used cannot be earned on a thin history; cap it at Present`);
  };

  const eras = list(report.eras, 'eras');
  if (eras.length === 0 && repo.noDivergence !== true) problems.push('eras: needs at least one era');
  if (eras.length > 0 && eras.filter((e) => e?.current === true).length !== 1) {
    problems.push('eras: exactly one era must have current: true');
  }
  eras.forEach((era, i) => {
    const at = `eras[${i}]`;
    text(era?.name, `${at}.name`);
    text(era?.summary, `${at}.summary`);
    date(era?.from, `${at}.from`);
    if (era?.current === true) {
      if (era?.to !== null) problems.push(`${at}.to: the current era must have to: null`);
    } else {
      date(era?.to, `${at}.to`);
    }
    list(era?.classification, `${at}.classification`).forEach((c, j) => {
      const cat = `${at}.classification[${j}]`;
      oneOf(c?.category, CATEGORIES, `${cat}.category`);
      text(c?.finding, `${cat}.finding`);
      label(c?.label, `${cat}.label`);
      citations(c?.citations, `${cat}.citations`);
    });
  });

  const seen = new Set();
  list(report.workflow, 'workflow').forEach((step, i) => {
    const at = `workflow[${i}]`;
    oneOf(step?.stage, STAGES, `${at}.stage`);
    if (seen.has(step?.stage)) problems.push(`${at}.stage: ${step?.stage} appears twice; combine its tools into one entry`);
    seen.add(step?.stage);
    if (step?.tool !== null) text(step?.tool, `${at}.tool`);
    label(step?.label, `${at}.label`);
    citations(step?.citations, `${at}.citations`);
  });

  list(report.practices, 'practices').forEach((p, i) => {
    const at = `practices[${i}]`;
    for (const key of ['title', 'what', 'why', 'cost']) text(p?.[key], `${at}.${key}`);
    oneOf(p?.label, ['Enforced', 'Used'], `${at}.label`);
    if (thin && p?.label === 'Used') problems.push(`${at}.label: Used cannot be earned on a thin history`);
    citations(p?.citations, `${at}.citations`);
  });

  list(report.inherited, 'inherited').forEach((item, i) => {
    text(item?.item, `inherited[${i}].item`);
    text(item?.source, `inherited[${i}].source`);
  });
  list(report.unknownTools, 'unknownTools').forEach((item, i) => {
    text(item?.path, `unknownTools[${i}].path`);
    text(item?.note, `unknownTools[${i}].note`);
  });
  list(report.suspected, 'suspected').forEach((item, i) => {
    text(item?.pattern, `suspected[${i}].pattern`);
    text(item?.note, `suspected[${i}].note`);
  });
  list(report.steeringAttempts, 'steeringAttempts').forEach((item, i) => {
    text(item?.path, `steeringAttempts[${i}].path`);
    text(item?.excerpt, `steeringAttempts[${i}].excerpt`);
  });

  const blindSpots = list(report.blindSpots, 'blindSpots');
  if (blindSpots.length === 0) problems.push('blindSpots: every report states its blind spots');
  blindSpots.forEach((b, i) => text(b, `blindSpots[${i}]`));

  list(report.skillMapping, 'skillMapping').forEach((m, i) => {
    const at = `skillMapping[${i}]`;
    text(m?.practice, `${at}.practice`);
    oneOf(m?.status, COVERAGE, `${at}.status`);
    if (m?.status !== 'Gap') text(m?.skill, `${at}.skill`);
    text(m?.note, `${at}.note`);
  });

  findEmails(report, 'report', problems);
  return { report, problems };
}

/* -------------------------------- ordering ------------------------------- */

const titleCase = (s) => s.charAt(0).toUpperCase() + s.slice(1);

/** Workflow steps in canonical stage order. */
export function orderedWorkflow(report) {
  return [...report.workflow].sort((a, b) => STAGES.indexOf(a.stage) - STAGES.indexOf(b.stage));
}

/** Current era first, then the rest newest first. */
export function orderedEras(report) {
  return [...report.eras].sort((a, b) => {
    if (a.current !== b.current) return a.current ? -1 : 1;
    return b.from.localeCompare(a.from);
  });
}

const shortSha = (report) => report.repo.sha.slice(0, 7);

function omittedDiagramNote(count) {
  const shown = count === 1 ? 'one stage' : 'no stages';
  return `Workflow diagram omitted: the evidence shows ${shown}, and a flow needs at least ${MIN_DIAGRAM_STAGES}.`;
}

/* ------------------------------ workflow SVG ----------------------------- */

const NODE_W = 176;
const NODE_H = 104;
const GAP_X = 52;
const GAP_Y = 64;
const PAD = 36;
const LEGEND_H = 44;
const SECONDS_PER_STAGE = 1.3;

/** Node positions, connector waypoints, and the pulse route for a list of steps. */
export function layoutWorkflow(count) {
  const perRow = Math.min(count, MAX_PER_ROW);
  const rows = Math.ceil(count / MAX_PER_ROW);
  const width = PAD * 2 + perRow * NODE_W + (perRow - 1) * GAP_X;
  const height = PAD * 2 + rows * NODE_H + (rows - 1) * GAP_Y + LEGEND_H;
  const nodes = Array.from({ length: count }, (_, i) => ({
    x: PAD + (i % MAX_PER_ROW) * (NODE_W + GAP_X),
    y: PAD + Math.floor(i / MAX_PER_ROW) * (NODE_H + GAP_Y),
  }));

  const connectors = [];
  for (let i = 0; i + 1 < count; i += 1) {
    const from = nodes[i];
    const to = nodes[i + 1];
    const exitX = from.x + NODE_W;
    const exitY = from.y + NODE_H / 2;
    const entryX = to.x;
    const entryY = to.y + NODE_H / 2;
    if (from.y === to.y) {
      connectors.push([[exitX, exitY], [entryX, entryY]]);
    } else {
      // Row wrap: step right, run back along the gap between rows, drop into the next row.
      const midY = from.y + NODE_H + GAP_Y / 2;
      const outX = exitX + GAP_X / 4;
      const inX = entryX - PAD / 2;
      connectors.push([[exitX, exitY], [outX, exitY], [outX, midY], [inX, midY], [inX, entryY], [entryX, entryY]]);
    }
  }
  return { width, height, nodes, connectors };
}

const dist = ([x1, y1], [x2, y2]) => Math.hypot(x2 - x1, y2 - y1);
const pct = (n) => `${Number(n.toFixed(2))}%`;

/** Keyframes for the pulse and per-stage glow. Numbers only, so no repo text reaches the CSS. */
function animationCss(layout) {
  const { nodes, connectors } = layout;
  const route = [];
  const arrivals = [0];
  let travelled = 0;
  connectors.forEach((points) => {
    points.forEach((point, i) => {
      if (route.length > 0 && i === 0) {
        // Crossing a node: the pulse passes behind the box to the exit edge.
        travelled += dist(route[route.length - 1].point, point);
      } else if (i > 0) {
        travelled += dist(points[i - 1], point);
      }
      route.push({ point, at: travelled });
    });
    arrivals.push(travelled);
  });
  const total = travelled || 1;
  const duration = (nodes.length * SECONDS_PER_STAGE).toFixed(1);

  const steps = route
    .map(({ point: [x, y], at }) => `${pct((at / total) * 92)}{transform:translate(${x}px,${y}px);opacity:1}`)
    .join('');
  const last = route[route.length - 1].point;
  const css = [
    `@keyframes hm-pulse{${steps}100%{transform:translate(${last[0]}px,${last[1]}px);opacity:0}}`,
    `.hm-pulse{animation:hm-pulse ${duration}s linear infinite}`,
  ];
  arrivals.forEach((at, i) => {
    const hit = (at / total) * 92;
    const before = Math.max(hit - 2, 0);
    const after = Math.min(hit + 7, 100);
    // Only the fill animates: stroke width and dashes carry the evidence label.
    const rest = '{fill:var(--panel)}';
    const lead = before > 0 ? `0%${rest}` : '';
    const trail = after < 100 ? `100%${rest}` : '';
    css.push(
      `@keyframes hm-glow-${i}{${lead}${pct(before)}${rest}${pct(hit + 1)}{fill:var(--glow)}${pct(after)}${rest}${trail}}`,
      `.hm-st-${i} .hm-box{animation:hm-glow-${i} ${duration}s linear infinite}`,
    );
  });
  css.push('.hm-flow{stroke:var(--accent);stroke-opacity:.55;stroke-width:2.5;stroke-dasharray:7 7;animation:hm-dash 1.1s linear infinite}');
  css.push('@keyframes hm-dash{to{stroke-dashoffset:-14}}', '.hm-pulse{display:inline}');
  return `@media (prefers-reduced-motion:no-preference){${css.join('')}}`;
}

/** Text alternative for the diagram; carries full names that the boxes may truncate. */
export function workflowDescription(steps) {
  return steps
    .map((s) => `${titleCase(s.stage)}${s.tool ? ` using ${s.tool}` : ''} (${s.label})`)
    .join(', then ');
}

/** Returns { svg, css } for the current-era workflow, or null below the stage threshold. */
export function renderWorkflowSvg(report) {
  const steps = orderedWorkflow(report);
  if (steps.length < MIN_DIAGRAM_STAGES) return null;

  const layout = layoutWorkflow(steps.length);
  const { width, height, nodes, connectors } = layout;

  const lines = connectors
    .map((points) => {
      const d = points.map(([x, y]) => `${x},${y}`).join(' ');
      return `<polyline class="hm-line" points="${d}" marker-end="url(#hm-arrow)"/><polyline class="hm-flow" points="${d}"/>`;
    })
    .join('');

  const boxes = steps
    .map((step, i) => {
      const { x, y } = nodes[i];
      const cx = NODE_W / 2;
      const tool = step.tool ? truncate(step.tool, MAX_TOOL_CHARS) : 'no named tool';
      const toolClass = step.tool ? 'hm-tool' : 'hm-tool hm-none';
      return (
        `<g class="hm-node hm-ev-${esc(step.label.toLowerCase())} hm-st-${i}" transform="translate(${x} ${y})">` +
        `<rect class="hm-box" width="${NODE_W}" height="${NODE_H}" rx="14"/>` +
        `<text class="hm-stage" x="${cx}" y="36">${esc(titleCase(step.stage))}</text>` +
        `<text class="${toolClass}" x="${cx}" y="60">${esc(tool)}</text>` +
        `<text class="hm-ev" x="${cx}" y="86">${esc(step.label.toUpperCase())}</text></g>`
      );
    })
    .join('');

  const legendY = height - PAD / 2 - LEGEND_H / 2;
  const legend = LABELS.map((name, i) => {
    const x = PAD + i * 132;
    return (
      `<g class="hm-node hm-ev-${name.toLowerCase()}" transform="translate(${x} ${legendY})">` +
      `<rect class="hm-box" width="30" height="18" rx="5"/>` +
      `<text class="hm-legend" x="40" y="14">${name}</text></g>`
    );
  }).join('');

  const description = workflowDescription(steps);
  const svg =
    `<svg class="hm-diagram" viewBox="0 0 ${width} ${height}" role="img" aria-labelledby="hm-t hm-d">` +
    `<title id="hm-t">Development workflow of ${esc(report.repo.owner)}/${esc(report.repo.name)}, current era</title>` +
    `<desc id="hm-d">${esc(description)}</desc>` +
    `<defs><marker id="hm-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">` +
    `<path class="hm-head" d="M0 0L10 5L0 10z"/></marker></defs>` +
    `${lines}<circle class="hm-pulse" r="7"/>${boxes}${legend}</svg>`;
  return { svg, css: animationCss(layout) };
}

/* ---------------------------------- HTML --------------------------------- */

const BASE_CSS = `
:root{--bg:#f7f6f2;--panel:#fff;--ink:#1d2027;--muted:#5d6472;--line:#d9d7cf;--accent:#3b5bdb;--enforced:#0b7a55;--used:#3b5bdb;--present:#8a6d1f;--warn-bg:#fff4dc;--warn:#7a5200;--pulse:#e8590c;--glow:#dfe6ff}
@media (prefers-color-scheme:dark){:root{--bg:#12141a;--panel:#1b1e27;--ink:#eceef3;--muted:#a3a9b8;--line:#333847;--accent:#8fa8ff;--enforced:#4fd1a5;--used:#8fa8ff;--present:#e0c068;--warn-bg:#33290f;--warn:#f0cf7a;--pulse:#ff9b5e;--glow:#2f3a63}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:1020px;margin:0 auto;padding:40px 24px 80px}
h1{font-size:2rem;line-height:1.2;margin:0 0 6px}
h2{font-size:1.35rem;margin:44px 0 12px;padding-bottom:6px;border-bottom:1px solid var(--line)}
h3{font-size:1.05rem;margin:24px 0 6px}
a{color:var(--accent)}
.hm-meta{color:var(--muted);margin:0 0 20px;font-size:.92rem}
.hm-lede{font-size:1.1rem}
.hm-banner{background:var(--warn-bg);color:var(--warn);border-radius:10px;padding:12px 16px;margin:14px 0}
.hm-banner ul{margin:6px 0 0;padding-left:20px}
.hm-panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:12px;margin:16px 0;overflow-x:auto}
.hm-caption{color:var(--muted);font-size:.88rem;margin:8px 8px 4px}
.hm-diagram{display:block;width:100%;min-width:640px;height:auto}
.hm-line{fill:none;stroke:var(--line);stroke-width:2.5}
.hm-flow{fill:none;stroke:none}
.hm-head{fill:var(--muted)}
.hm-pulse{fill:var(--pulse);display:none}
.hm-box{fill:var(--panel);stroke:var(--muted);stroke-width:2;stroke-opacity:.85}
.hm-ev-enforced .hm-box{stroke:var(--enforced);stroke-width:3.5}
.hm-ev-used .hm-box{stroke:var(--used)}
.hm-ev-present .hm-box{stroke:var(--present);stroke-dasharray:7 6}
.hm-stage{fill:var(--ink);font-size:19px;font-weight:650;text-anchor:middle}
.hm-tool{fill:var(--muted);font-size:13.5px;text-anchor:middle}
.hm-none{font-style:italic}
.hm-ev{font-size:11px;font-weight:700;letter-spacing:.09em;text-anchor:middle}
.hm-ev-enforced .hm-ev{fill:var(--enforced)}
.hm-ev-used .hm-ev{fill:var(--used)}
.hm-ev-present .hm-ev{fill:var(--present)}
.hm-legend{fill:var(--muted);font-size:13px}
table{width:100%;border-collapse:collapse;font-size:.93rem}
th,td{text-align:left;vertical-align:top;padding:8px 10px;border-bottom:1px solid var(--line)}
th{color:var(--muted);font-weight:600}
.hm-tag{display:inline-block;padding:0 8px;border:1.5px solid currentColor;border-radius:999px;font-size:.76rem;font-weight:700;white-space:nowrap}
.hm-tag-enforced{color:var(--enforced)}
.hm-tag-used{color:var(--used)}
.hm-tag-present{color:var(--present);border-style:dashed}
.hm-cites{font-size:.85rem;color:var(--muted)}
code{font-size:.88em;overflow-wrap:anywhere}
`;

function citationsHtml(citations) {
  return citations
    .map((c) => {
      const href = safeHref(c.url);
      return href
        ? `<a href="${esc(href)}" rel="noopener noreferrer">${esc(c.text)}</a>`
        : esc(c.text);
    })
    .join(', ');
}

const tagHtml = (label) => `<span class="hm-tag hm-tag-${esc(label.toLowerCase())}">${esc(label)}</span>`;
const listHtml = (items) => `<ul>${items.map((i) => `<li>${esc(i)}</li>`).join('')}</ul>`;

function bannerHtml(report) {
  const parts = [];
  if (report.repo.visibility === 'private') {
    parts.push('<div class="hm-banner"><strong>Private source.</strong> This report describes a private repository. Check before sharing it.</div>');
  }
  if (report.limitations.length > 0) {
    parts.push(`<div class="hm-banner"><strong>Limitations.</strong>${listHtml(report.limitations)}</div>`);
  }
  return parts.join('');
}

function eraHtml(era) {
  const span = `${era.from} to ${era.to ?? 'now'}`;
  const rows = era.classification
    .map((c) => `<tr><td>${esc(c.category)}</td><td>${esc(c.finding)}</td><td>${tagHtml(c.label)}</td><td class="hm-cites">${citationsHtml(c.citations)}</td></tr>`)
    .join('');
  const table = rows
    ? `<table><thead><tr><th scope="col">Category</th><th scope="col">Finding</th><th scope="col">Evidence</th><th scope="col">Citations</th></tr></thead><tbody>${rows}</tbody></table>`
    : '<p>No process signals were found in this era.</p>';
  return `<h3>${esc(era.name)}${era.current ? ' (current)' : ''} <span class="hm-cites">${esc(span)}</span></h3><p>${esc(era.summary)}</p>${table}`;
}

function workflowHtml(report, diagram) {
  const steps = orderedWorkflow(report);
  if (report.repo.noDivergence === true) return '';
  const current = report.eras.find((e) => e.current);
  const heading = '<h2>Development workflow</h2>';
  if (!diagram) return `${heading}<p>${esc(omittedDiagramNote(steps.length))}</p>`;
  const rows = steps
    .map((s) => `<tr><td>${esc(titleCase(s.stage))}</td><td>${esc(s.tool ?? 'no named tool')}</td><td>${tagHtml(s.label)}</td><td class="hm-cites">${citationsHtml(s.citations)}</td></tr>`)
    .join('');
  return (
    `${heading}<div class="hm-panel">${diagram.svg}` +
    `<p class="hm-caption">${esc(current.name)}, since ${esc(current.from)}, at commit ${esc(shortSha(report))}. ` +
    'The line shows the usual order of stages, not a promise that every change passes through each one.</p></div>' +
    `<table><thead><tr><th scope="col">Stage</th><th scope="col">Tool</th><th scope="col">Evidence</th><th scope="col">Citations</th></tr></thead><tbody>${rows}</tbody></table>`
  );
}

/** One sentence naming a fork, template, or mirror parent, or null for original work. */
function lineageText(report) {
  const { relationship, upstream } = report.repo;
  if (relationship === 'original') return null;
  const noun = { fork: 'Fork of', template: 'Generated from template', mirror: 'Mirror of' }[relationship];
  return `${noun} ${upstream ?? 'an upstream repository'}. Only work after the divergence point is classified.`;
}

function coverageLine(report) {
  const { commitsScanned, prsSampled, prsTotal, gh } = report.coverage;
  return `${commitsScanned} commits scanned. ${prsSampled} of ${prsTotal} pull requests sampled. GitHub API: ${gh}.`;
}

export function renderHtml(report) {
  const { owner, name, sha, analyzedAt, subpath } = report.repo;
  const diagram = report.repo.noDivergence === true ? null : renderWorkflowSvg(report);
  const css = `${BASE_CSS}${diagram?.css ?? ''}`;
  const hash = crypto.createHash('sha256').update(css, 'utf8').digest('base64');
  const csp = `default-src 'none'; style-src 'sha256-${hash}'; base-uri 'none'; form-action 'none'`;
  const treeUrl = `https://github.com/${owner}/${name}/tree/${sha}`;

  const sections = [];
  sections.push(`<p class="hm-lede">${esc(report.summary)}</p>`);
  if (report.repo.noDivergence === true) {
    const href = safeHref(report.repo.upstream);
    sections.push(`<div class="hm-banner"><strong>Nothing to classify.</strong> This repository has not diverged from its upstream. Analyse <a href="${esc(href)}" rel="noopener noreferrer">${esc(href)}</a> instead.</div>`);
  }
  sections.push(workflowHtml(report, diagram));
  if (report.narrative.length > 0) {
    sections.push(`<h2>How it was built</h2>${report.narrative.map((p) => `<p>${esc(p)}</p>`).join('')}`);
  }
  if (report.eras.length > 0) {
    sections.push(`<h2>Classification by era</h2>${orderedEras(report).map(eraHtml).join('')}`);
  }
  if (report.practices.length > 0) {
    const items = report.practices
      .map((p) => `<h3>${esc(p.title)} ${tagHtml(p.label)}</h3><p>${esc(p.what)}</p><p><strong>Why it seems to work:</strong> ${esc(p.why)}</p><p><strong>Cost to adopt:</strong> ${esc(p.cost)}</p><p class="hm-cites">${citationsHtml(p.citations)}</p>`)
      .join('');
    sections.push(`<h2>Practices worth copying</h2>${items}`);
  }
  if (report.inherited.length > 0) {
    sections.push(`<h2>Inherited, not authored here</h2>${listHtml(report.inherited.map((i) => `${i.item} (from ${i.source})`))}`);
  }
  if (report.unknownTools.length > 0) {
    const rows = report.unknownTools.map((u) => `<li><code>${esc(u.path)}</code>: ${esc(u.note)}</li>`).join('');
    sections.push(`<h2>Unknown tools</h2><ul>${rows}</ul>`);
  }
  if (report.suspected.length > 0) {
    const rows = report.suspected.map((s) => `<li><strong>${esc(s.pattern)}</strong>: ${esc(s.note)}</li>`).join('');
    sections.push(`<h2>Suspected, not established</h2><p>These patterns correlate with agent use but also describe careful human work. They do not feed the classification.</p><ul>${rows}</ul>`);
  }
  sections.push(`<h2>Blind spots</h2><p>Absence of evidence here is not evidence of absence.</p>${listHtml(report.blindSpots)}`);
  if (report.steeringAttempts.length > 0) {
    const rows = report.steeringAttempts.map((s) => `<li><code>${esc(s.path)}</code>: <code>${esc(s.excerpt)}</code></li>`).join('');
    sections.push(`<h2>Text that tried to steer the analysis</h2><p>This text was treated as data and not followed.</p><ul>${rows}</ul>`);
  }
  sections.push(`<h2>Coverage</h2><p>${esc(coverageLine(report))}</p>`);
  if (report.skillMapping.length > 0) {
    const rows = report.skillMapping
      .map((m) => `<tr><td>${esc(m.practice)}</td><td>${esc(m.status)}</td><td>${esc(m.skill ?? '')}</td><td>${esc(m.note)}</td></tr>`)
      .join('');
    sections.push(`<h2>Your skill coverage</h2><p>Personal to the machine that ran this report. Remove this section before sharing.</p><table><thead><tr><th scope="col">Practice</th><th scope="col">Status</th><th scope="col">Skill</th><th scope="col">Note</th></tr></thead><tbody>${rows}</tbody></table>`);
  }

  const scope = subpath ? ` (${subpath})` : '';
  const lineage = lineageText(report);
  return (
    '<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8">' +
    `<meta http-equiv="Content-Security-Policy" content="${esc(csp)}">` +
    '<meta name="viewport" content="width=device-width, initial-scale=1">' +
    `<title>How it's made: ${esc(owner)}/${esc(name)}</title><style>${css}</style></head><body><main>` +
    `<h1>How it's made: ${esc(owner)}/${esc(name)}${esc(scope)}</h1>` +
    `<p class="hm-meta">Analysed ${esc(analyzedAt)} at commit <a href="${esc(treeUrl)}" rel="noopener noreferrer">${esc(shortSha(report))}</a>.${lineage ? ` ${esc(lineage)}` : ''}</p>` +
    `${bannerHtml(report)}${sections.join('')}</main></body></html>\n`
  );
}

/* -------------------------------- Markdown ------------------------------- */

function citationsMd(citations) {
  return citations
    .map((c) => {
      const href = safeHref(c.url);
      return href ? `[${mdText(c.text)}](<${href.replace(/[<>]/g, encodeURIComponent)}>)` : mdText(c.text);
    })
    .join(', ');
}

const bullets = (items) => items.map((i) => `- ${i}`).join('\n');

function tableMd(headers, rows) {
  return [
    `| ${headers.join(' | ')} |`,
    `| ${headers.map(() => '---').join(' | ')} |`,
    ...rows.map((r) => `| ${r.join(' | ')} |`),
  ].join('\n');
}

export function renderMarkdown(report) {
  const { owner, name, sha, analyzedAt, subpath } = report.repo;
  const steps = orderedWorkflow(report);
  const out = [];
  const scope = subpath ? ` (${mdText(subpath)})` : '';
  out.push(`# How it's made: ${owner}/${mdText(name)}${scope}`);
  out.push(`Analysed ${analyzedAt} at commit [${shortSha(report)}](https://github.com/${owner}/${name}/tree/${sha}).`);
  if (lineageText(report)) out.push(mdText(lineageText(report)));
  if (report.repo.visibility === 'private') {
    out.push('> **Private source.** This report describes a private repository. Check before sharing it.');
  }
  if (report.limitations.length > 0) {
    out.push(`**Limitations**\n\n${bullets(report.limitations.map(mdText))}`);
  }
  out.push(mdText(report.summary));
  if (report.repo.noDivergence === true) {
    out.push(`**Nothing to classify.** This repository has not diverged from its upstream. Analyse <${safeHref(report.repo.upstream)}> instead.`);
  } else {
    out.push('## Development workflow');
    if (steps.length >= MIN_DIAGRAM_STAGES) {
      out.push(mdText(workflowDescription(steps)));
      out.push(tableMd(
        ['Stage', 'Tool', 'Evidence', 'Citations'],
        steps.map((s) => [titleCase(s.stage), mdText(s.tool ?? 'no named tool'), s.label, citationsMd(s.citations)]),
      ));
    } else {
      out.push(omittedDiagramNote(steps.length));
    }
  }
  if (report.narrative.length > 0) {
    out.push('## How it was built', ...report.narrative.map(mdText));
  }
  if (report.eras.length > 0) {
    out.push('## Classification by era');
    orderedEras(report).forEach((era) => {
      out.push(`### ${mdText(era.name)}${era.current ? ' (current)' : ''}, ${era.from} to ${era.to ?? 'now'}`);
      out.push(mdText(era.summary));
      if (era.classification.length > 0) {
        out.push(tableMd(
          ['Category', 'Finding', 'Evidence', 'Citations'],
          era.classification.map((c) => [c.category, mdText(c.finding), c.label, citationsMd(c.citations)]),
        ));
      } else {
        out.push('No process signals were found in this era.');
      }
    });
  }
  if (report.practices.length > 0) {
    out.push('## Practices worth copying');
    report.practices.forEach((p) => {
      out.push(`### ${mdText(p.title)} (${p.label})`);
      out.push(mdText(p.what));
      out.push(`**Why it seems to work:** ${mdText(p.why)}`);
      out.push(`**Cost to adopt:** ${mdText(p.cost)}`);
      out.push(`Evidence: ${citationsMd(p.citations)}`);
    });
  }
  if (report.inherited.length > 0) {
    out.push('## Inherited, not authored here', bullets(report.inherited.map((i) => `${mdText(i.item)} (from ${mdText(i.source)})`)));
  }
  if (report.unknownTools.length > 0) {
    out.push('## Unknown tools', bullets(report.unknownTools.map((u) => `${mdText(u.path)}: ${mdText(u.note)}`)));
  }
  if (report.suspected.length > 0) {
    out.push('## Suspected, not established');
    out.push('These patterns correlate with agent use but also describe careful human work. They do not feed the classification.');
    out.push(bullets(report.suspected.map((s) => `**${mdText(s.pattern)}**: ${mdText(s.note)}`)));
  }
  out.push('## Blind spots', 'Absence of evidence here is not evidence of absence.', bullets(report.blindSpots.map(mdText)));
  if (report.steeringAttempts.length > 0) {
    out.push('## Text that tried to steer the analysis', 'This text was treated as data and not followed.');
    out.push(bullets(report.steeringAttempts.map((s) => `${mdText(s.path)}: ${mdText(s.excerpt)}`)));
  }
  out.push('## Coverage', coverageLine(report));
  if (report.skillMapping.length > 0) {
    out.push('## Your skill coverage', 'Personal to the machine that ran this report. Remove this section before sharing.');
    out.push(tableMd(
      ['Practice', 'Status', 'Skill', 'Note'],
      report.skillMapping.map((m) => [mdText(m.practice), m.status, mdText(m.skill ?? ''), mdText(m.note)]),
    ));
  }
  return `${out.join('\n\n')}\n`;
}

/* ----------------------------------- CLI --------------------------------- */

function main(argv) {
  if (argv.length !== 1 || !argv[0].endsWith('.json')) {
    console.error('Usage: node render-report.mjs <report.json>');
    return 2;
  }
  const input = path.resolve(argv[0]);
  let parsed;
  try {
    parsed = JSON.parse(fs.readFileSync(input, 'utf8'));
  } catch (error) {
    console.error(`Cannot read ${input}: ${error.message}`);
    return 1;
  }
  const { report, problems } = validateReport(parsed);
  if (problems.length > 0) {
    console.error(`Report rejected, ${problems.length} problem(s):`);
    problems.forEach((p) => console.error(`  - ${p}`));
    return 1;
  }
  const base = input.slice(0, -'.json'.length);
  fs.writeFileSync(`${base}.md`, renderMarkdown(report));
  fs.writeFileSync(`${base}.html`, renderHtml(report));
  console.log(`Wrote ${base}.md`);
  console.log(`Wrote ${base}.html`);
  return 0;
}

if (process.argv[1] && import.meta.url === pathToFileURL(fs.realpathSync(process.argv[1])).href) {
  process.exitCode = main(process.argv.slice(2));
}
