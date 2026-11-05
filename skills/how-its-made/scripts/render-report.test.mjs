import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';

import {
  esc,
  layoutWorkflow,
  mdText,
  orderedEras,
  orderedWorkflow,
  renderHtml,
  renderMarkdown,
  renderWorkflowSvg,
  safeHref,
  truncate,
  validateReport,
} from './render-report.mjs';

const SCRIPT = fileURLToPath(new URL('./render-report.mjs', import.meta.url));
const cite = [{ text: 'abc1234', url: 'https://github.com/acme/widget/commit/abc1234' }];

function sample(overrides = {}) {
  return {
    repo: {
      owner: 'acme',
      name: 'widget',
      sha: 'a'.repeat(40),
      analyzedAt: '2026-11-05',
      visibility: 'public',
      relationship: 'original',
    },
    summary: 'A spec-driven project.',
    narrative: ['It began by hand.'],
    limitations: [],
    history: { quality: 'full' },
    coverage: { commitsScanned: 120, prsSampled: 30, prsTotal: 80, gh: 'available' },
    eras: [
      { name: 'Hand-written', from: '2024-01-01', to: '2025-12-31', current: false, summary: 'Manual.', classification: [] },
      {
        name: 'Spec-driven',
        from: '2026-01-01',
        to: null,
        current: true,
        summary: 'Specs first.',
        classification: [{ category: 'framework', finding: 'SpecKit', label: 'Used', citations: cite }],
      },
    ],
    workflow: [
      { stage: 'review', tool: 'CodeRabbit', label: 'Used', citations: cite },
      { stage: 'spec', tool: 'SpecKit', label: 'Used', citations: cite },
      { stage: 'merge', tool: null, label: 'Enforced', citations: cite },
    ],
    practices: [],
    inherited: [],
    unknownTools: [],
    suspected: [],
    steeringAttempts: [],
    blindSpots: ['Local agent config is not committed.'],
    skillMapping: [],
    ...overrides,
  };
}

const valid = (report) => {
  const result = validateReport(report);
  assert.deepEqual(result.problems, []);
  return result.report;
};
const problemsOf = (report) => validateReport(report).problems.join('\n');

describe('text safety', () => {
  it('escapes HTML metacharacters', () => {
    assert.equal(esc(`<a href="x">'&`), '&lt;a href=&quot;x&quot;&gt;&#39;&amp;');
  });

  it('allows only http and https links', () => {
    assert.equal(safeHref('https://example.com/a'), 'https://example.com/a');
    assert.equal(safeHref('http://example.com/'), 'http://example.com/');
    const bad = ['javascript:alert(1)', 'JaVaScRiPt:alert(1)', ' javascript:alert(1)', 'data:text/html,x', 'file:///etc/passwd', 'vbscript:x', '/relative', '', null, 42];
    for (const url of bad) assert.equal(safeHref(url), null, String(url));
  });

  it('truncates by code point without splitting emoji', () => {
    assert.equal(truncate('short', 20), 'short');
    assert.equal(truncate('😀😀😀😀', 3), '😀😀…');
  });

  it('neutralises Markdown and raw HTML', () => {
    assert.equal(mdText('<img src=x>'), '\\<img src=x\\>');
    assert.equal(mdText('[x](javascript:y)'), '\\[x\\](javascript:y)');
    assert.equal(mdText('line\nbreak | pipe'), 'line break \\| pipe');
  });
});

describe('validation', () => {
  it('accepts a good report', () => {
    valid(sample());
  });

  it('rejects non-objects', () => {
    for (const bad of [null, [], 'x', 3]) assert.match(validateReport(bad).problems[0], /JSON object/);
  });

  it('rejects a malformed SHA, owner, and impossible date', () => {
    const repo = { ...sample().repo, sha: 'abc', owner: '-bad-', analyzedAt: '2026-02-30' };
    const out = problemsOf(sample({ repo }));
    assert.match(out, /repo\.sha/);
    assert.match(out, /repo\.owner/);
    assert.match(out, /repo\.analyzedAt/);
  });

  it('accepts a leap day and rejects a false one', () => {
    valid(sample({ repo: { ...sample().repo, analyzedAt: '2024-02-29' } }));
    assert.match(problemsOf(sample({ repo: { ...sample().repo, analyzedAt: '2025-02-29' } })), /analyzedAt/);
  });

  it('requires a citation on every workflow stage', () => {
    const workflow = [{ stage: 'spec', tool: 'SpecKit', label: 'Used', citations: [] }];
    assert.match(problemsOf(sample({ workflow })), /needs at least one citation/);
  });

  it('keeps Suspected out of the workflow', () => {
    const workflow = [{ stage: 'code', tool: 'Claude', label: 'Suspected', citations: cite }];
    assert.match(problemsOf(sample({ workflow })), /workflow\[0\]\.label/);
  });

  it('caps claims at Present on a thin history', () => {
    const out = problemsOf(sample({ history: { quality: 'thin' }, limitations: ['One commit.'] }));
    assert.match(out, /workflow\[0\]\.label: Used cannot be earned/);
    assert.match(out, /eras\[1\]\.classification\[0\]\.label: Used cannot be earned/);
  });

  it('demands limitations when history is thin or gh evidence is missing', () => {
    const noGh = sample({ coverage: { ...sample().coverage, gh: 'rate-limited' } });
    assert.match(problemsOf(noGh), /limitations: must explain/);
    valid({ ...noGh, limitations: ['PR evidence is absent.'] });
  });

  it('requires exactly one current era', () => {
    const eras = sample().eras.map((e) => ({ ...e, current: false }));
    assert.match(problemsOf(sample({ eras })), /exactly one era/);
  });

  it('requires an end date on past eras and none on the current era', () => {
    const [past, current] = sample().eras;
    assert.match(problemsOf(sample({ eras: [{ ...past, to: null }, current] })), /eras\[0\]\.to: must be a real/);
    assert.match(problemsOf(sample({ eras: [past, { ...current, to: '2026-02-01' }] })), /eras\[1\]\.to: the current era/);
  });

  it('rejects a duplicate workflow stage', () => {
    const step = { stage: 'code', tool: 'A', label: 'Used', citations: cite };
    assert.match(problemsOf(sample({ workflow: [step, step] })), /appears twice/);
  });

  it('rejects emails anywhere in the report', () => {
    assert.match(problemsOf(sample({ summary: 'Mail dev@example.com now' })), /report\.summary: contains an email/);
    const steeringAttempts = [{ path: 'CLAUDE.md', excerpt: 'Co-Authored-By: Bot <noreply@anthropic.com>' }];
    assert.match(problemsOf(sample({ steeringAttempts })), /steeringAttempts\[0\]\.excerpt/);
  });

  it('always requires blind spots', () => {
    assert.match(problemsOf(sample({ blindSpots: [] })), /blindSpots/);
  });

  it('requires an upstream when a fork has not diverged', () => {
    const repo = { ...sample().repo, relationship: 'fork', noDivergence: true };
    assert.match(problemsOf(sample({ repo, eras: [], workflow: [] })), /repo\.upstream/);
    valid(sample({ repo: { ...repo, upstream: 'https://github.com/up/stream' }, eras: [], workflow: [] }));
  });

  it('strips bidi overrides and control characters', () => {
    const { report } = validateReport(sample({ summary: 'safe‮txt.exe\u0007' }));
    assert.equal(report.summary, 'safetxt.exe');
  });
});

describe('ordering', () => {
  it('sorts stages canonically regardless of input order', () => {
    assert.deepEqual(orderedWorkflow(sample()).map((s) => s.stage), ['spec', 'review', 'merge']);
  });

  it('puts the current era first, then newest first', () => {
    const eras = [
      { name: 'old', from: '2020-01-01', current: false },
      { name: 'mid', from: '2023-01-01', current: false },
      { name: 'now', from: '2022-01-01', current: true },
    ];
    assert.deepEqual(orderedEras({ eras }).map((e) => e.name), ['now', 'mid', 'old']);
  });
});

describe('workflow diagram', () => {
  it('is omitted below two stages, with the reason given', () => {
    for (const workflow of [[], [{ stage: 'code', tool: null, label: 'Present', citations: cite }]]) {
      const report = valid(sample({ workflow }));
      assert.equal(renderWorkflowSvg(report), null);
      assert.match(renderHtml(report), /Workflow diagram omitted/);
      assert.match(renderMarkdown(report), /Workflow diagram omitted/);
      assert.doesNotMatch(renderHtml(report), /<svg/);
    }
  });

  it('draws at exactly two stages', () => {
    assert.ok(renderWorkflowSvg(valid(sample({ workflow: sample().workflow.slice(0, 2) }))));
  });

  it('wraps past five stages onto a second row', () => {
    const one = layoutWorkflow(5);
    const two = layoutWorkflow(7);
    assert.equal(new Set(one.nodes.map((n) => n.y)).size, 1);
    assert.equal(new Set(two.nodes.map((n) => n.y)).size, 2);
    assert.equal(two.connectors.length, 6);
    assert.equal(two.connectors[4].length, 6, 'the wrap connector has elbows');
    for (const n of two.nodes) assert.ok(n.x + 176 <= two.width && n.y + 104 <= two.height);
    for (const [x] of two.connectors.flat()) assert.ok(x >= 0 && x <= two.width);
  });

  it('labels evidence in words and is exposed as an image with a description', () => {
    const { svg } = renderWorkflowSvg(valid(sample()));
    assert.match(svg, /role="img"/);
    assert.match(svg, /aria-labelledby="hm-t hm-d"/);
    assert.match(svg, />ENFORCED</);
    assert.match(svg, />USED</);
    assert.match(svg, /<desc id="hm-d">Spec using SpecKit \(Used\), then Review using CodeRabbit \(Used\), then Merge \(Enforced\)/);
  });

  it('truncates a long tool in the box and keeps it whole in the description', () => {
    const long = 'A-very-long-tool-name-that-overflows-the-box';
    const workflow = [
      { stage: 'code', tool: long, label: 'Used', citations: cite },
      { stage: 'test', tool: null, label: 'Used', citations: cite },
    ];
    const { svg } = renderWorkflowSvg(valid(sample({ workflow })));
    assert.match(svg, /A-very-long-tool-na…</);
    assert.ok(svg.includes(`<desc id="hm-d">Code using ${long}`));
  });

  it('escapes a hostile tool name', () => {
    const workflow = [
      { stage: 'code', tool: '</text><script>alert(1)</script>', label: 'Used', citations: cite },
      { stage: 'test', tool: 'x', label: 'Used', citations: cite },
    ];
    const html = renderHtml(valid(sample({ workflow })));
    assert.doesNotMatch(html, /<script/i);
    assert.match(html, /&lt;\/text&gt;/);
  });

  it('animates only the fill, so the evidence styling never changes', () => {
    const { css } = renderWorkflowSvg(valid(sample()));
    const glows = css.match(/@keyframes hm-glow-\d+\{.*?\}\}/g);
    assert.equal(glows.length, 3);
    for (const glow of glows) assert.doesNotMatch(glow, /stroke/);
  });

  it('moves the pulse forward through every waypoint', () => {
    const { css } = renderWorkflowSvg(valid(sample()));
    const steps = /@keyframes hm-pulse\{(.*?)\}\}/.exec(css)[1];
    const stops = [...steps.matchAll(/([\d.]+)%\{/g)].map((m) => Number(m[1]));
    assert.equal(stops[0], 0);
    assert.deepEqual(stops, [...stops].sort((a, b) => a - b));
    assert.equal(new Set(stops).size, stops.length, 'no duplicate stops');
  });

  it('keeps the pulse opaque until the end of its route', () => {
    const { css } = renderWorkflowSvg(valid(sample()));
    const steps = /@keyframes hm-pulse\{(.*?)\}\}/.exec(css)[1];
    const stops = steps.split('}').filter((s) => !s.startsWith('100%'));
    for (const stop of stops) assert.match(stop, /opacity:1/);
  });

  it('runs all motion inside a reduced-motion guard, with the pulse hidden otherwise', () => {
    const report = valid(sample());
    const { css } = renderWorkflowSvg(report);
    assert.ok(css.startsWith('@media (prefers-reduced-motion:no-preference){'));
    assert.match(css, /\.hm-pulse\{display:inline\}/);
    assert.match(renderHtml(report), /\.hm-pulse\{fill:var\(--pulse\);display:none\}/);
  });
});

describe('html page', () => {
  it('carries a CSP whose hash matches its stylesheet, and no script or inline style', () => {
    const html = renderHtml(valid(sample()));
    const css = /<style>([\s\S]*?)<\/style>/.exec(html)[1];
    const hash = createHash('sha256').update(css, 'utf8').digest('base64');
    assert.ok(html.includes(`style-src &#39;sha256-${hash}&#39;`));
    assert.match(html, /default-src &#39;none&#39;/);
    assert.doesNotMatch(html, /<script/i);
    assert.doesNotMatch(html, /\sstyle="/);
    assert.doesNotMatch(html, /\son[a-z]+="/);
  });

  it('renders a hostile citation link as plain text', () => {
    const workflow = [
      { stage: 'code', tool: 'x', label: 'Used', citations: [{ text: 'click', url: 'javascript:alert(1)' }] },
      { stage: 'test', tool: 'y', label: 'Used', citations: cite },
    ];
    const report = valid(sample({ workflow }));
    assert.doesNotMatch(renderHtml(report), /javascript:/);
    assert.doesNotMatch(renderMarkdown(report), /\]\(<?javascript:/);
  });

  it('escapes hostile text in every free-text section', () => {
    const evil = '<img src=x onerror=alert(1)>';
    const report = valid(sample({
      summary: evil,
      narrative: [evil],
      limitations: [evil],
      inherited: [{ item: evil, source: evil }],
      unknownTools: [{ path: evil, note: evil }],
      suspected: [{ pattern: evil, note: evil }],
      steeringAttempts: [{ path: evil, excerpt: evil }],
      blindSpots: [evil],
      skillMapping: [{ practice: evil, status: 'Gap', note: evil }],
      practices: [{ title: evil, what: evil, why: evil, cost: evil, label: 'Used', citations: [{ text: evil }] }],
    }));
    assert.doesNotMatch(renderHtml(report), /<img/);
    assert.doesNotMatch(renderMarkdown(report), /(^|[^\\])<img/);
  });

  it('flags private sources, lineage, and undiverged forks', () => {
    const repo = { ...sample().repo, visibility: 'private', relationship: 'fork', noDivergence: true, upstream: 'https://github.com/up/stream' };
    const report = valid(sample({ repo, eras: [], workflow: [] }));
    const html = renderHtml(report);
    assert.match(html, /Private source/);
    assert.match(html, /Fork of https:\/\/github\.com\/up\/stream/);
    assert.match(html, /Nothing to classify/);
    assert.doesNotMatch(html, /Development workflow/);
    assert.match(renderMarkdown(report), /Nothing to classify/);
  });

  it('keeps skill coverage as the final section, and only when present', () => {
    assert.doesNotMatch(renderHtml(valid(sample())), /Your skill coverage/);
    const report = valid(sample({ skillMapping: [{ practice: 'Specs', status: 'Covered', skill: 'to-spec', note: 'Close.' }] }));
    for (const out of [renderHtml(report), renderMarkdown(report)]) {
      assert.ok(out.indexOf('Your skill coverage') > out.indexOf('Coverage'));
      assert.ok(out.indexOf('Your skill coverage') > out.indexOf('Blind spots'));
    }
  });
});

describe('command line', () => {
  const run = (...args) => spawnSync(process.execPath, [SCRIPT, ...args], { encoding: 'utf8' });

  it('writes both files beside the input', () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'hm-'));
    const input = path.join(dir, 'acme-widget-2026-11-05.json');
    fs.writeFileSync(input, JSON.stringify(sample()));
    execFileSync(process.execPath, [SCRIPT, input]);
    assert.ok(fs.existsSync(path.join(dir, 'acme-widget-2026-11-05.md')));
    assert.ok(fs.existsSync(path.join(dir, 'acme-widget-2026-11-05.html')));
    fs.rmSync(dir, { recursive: true });
  });

  it('refuses a bad report, lists the problems, and writes nothing', () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'hm-'));
    const input = path.join(dir, 'bad.json');
    fs.writeFileSync(input, JSON.stringify(sample({ blindSpots: [] })));
    const result = run(input);
    assert.equal(result.status, 1);
    assert.match(result.stderr, /blindSpots/);
    assert.deepEqual(fs.readdirSync(dir), ['bad.json']);
    fs.rmSync(dir, { recursive: true });
  });

  it('explains usage and unreadable input', () => {
    assert.equal(run().status, 2);
    assert.match(run('missing.json').stderr, /Cannot read/);
  });
});
