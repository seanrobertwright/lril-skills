import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';

import {
  ChecklistError,
  MAX_STEPS,
  build,
  inline,
  paragraphs,
  renderHtml,
  safeHref,
  slugOf,
  validateChecklist,
} from './build-checklist.mjs';

const SCRIPT = fileURLToPath(new URL('./build-checklist.mjs', import.meta.url));
const EXAMPLE = fileURLToPath(new URL('../example-checklist.json', import.meta.url));

function sample(overrides = {}) {
  return {
    title: 'Turn it off and on again',
    summary: 'Restart the app so it picks up the new setting.',
    steps: [
      { title: 'Close the app', do: 'Click the **X** in the corner.', why: 'Like closing a book before you reopen it.' },
      { title: 'Open the app', do: 'Double-click its icon.', why: 'A fresh start reads the new setting.' },
    ],
    ...overrides,
  };
}

function tmpDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'help-me-test-'));
}

function problem(raw, pattern) {
  assert.throws(() => validateChecklist(raw), (err) => err instanceof ChecklistError && pattern.test(err.message));
}

describe('validateChecklist', () => {
  it('accepts the shipped example', () => {
    const checklist = validateChecklist(JSON.parse(fs.readFileSync(EXAMPLE, 'utf8')));
    assert.ok(checklist.steps.length > 0);
    assert.ok(checklist.steps.every((s) => s.why));
  });

  it('rejects a checklist that is not an object', () => {
    problem([], /JSON object/);
    problem(null, /JSON object/);
  });

  it('requires a title, a summary and at least one step', () => {
    problem(sample({ title: '  ' }), /title is empty/);
    problem(sample({ summary: undefined }), /summary is missing/);
    problem(sample({ steps: [] }), /at least one step/);
    problem(sample({ steps: 'do it' }), /steps must be a list/);
  });

  it('requires every step to say what to do and why', () => {
    problem(sample({ steps: [{ title: 'A', do: 'x' }] }), /step 1 why is missing/);
    problem(sample({ steps: [{ title: 'A', why: 'x' }] }), /step 1 do is missing/);
    problem(sample({ steps: [{ title: 'A', do: 5, why: 'x' }] }), /step 1 do must be text/);
  });

  it('rejects two steps with the same title', () => {
    const step = { title: 'Press Enter', do: 'x', why: 'y' };
    problem(sample({ steps: [step, { ...step, title: 'press enter' }] }), /same title/);
  });

  it('caps the number of steps', () => {
    const steps = Array.from({ length: MAX_STEPS + 1 }, (_, i) => ({ title: `Step ${i}`, do: 'x', why: 'y' }));
    problem(sample({ steps }), /Split the task/);
  });

  it('checks minutes is a sensible whole number', () => {
    problem(sample({ minutes: '5' }), /minutes must be a whole number/);
    problem(sample({ minutes: 0 }), /minutes must be a whole number/);
    problem(sample({ minutes: Number.NaN }), /minutes must be a whole number/);
    assert.equal(validateChecklist(sample({ minutes: 5 })).minutes, 5);
  });

  it('only allows web and mail links as the source', () => {
    problem(sample({ sourceUrl: 'javascript:alert(1)' }), /sourceUrl must start with/);
    assert.equal(validateChecklist(sample({ sourceUrl: 'https://example.com/i/1' })).sourceUrl, 'https://example.com/i/1');
  });

  it('checks the paste block and keeps its text as written', () => {
    const base = { title: 'A', do: 'x', why: 'y' };
    problem(sample({ steps: [{ ...base, paste: 'npm test' }] }), /paste must be an object/);
    problem(sample({ steps: [{ ...base, paste: { text: ' ', into: 'the terminal' } }] }), /paste\.text is missing/);
    problem(sample({ steps: [{ ...base, paste: { text: 'npm test' } }] }), /paste\.into is missing/);
    const ok = validateChecklist(sample({ steps: [{ ...base, paste: { text: '  npm test\r\n', into: 'the terminal' } }] }));
    assert.equal(ok.steps[0].paste.text, '  npm test');
  });
});

describe('inline and paragraphs', () => {
  it('escapes HTML', () => {
    assert.equal(inline('<script>"x"</script>'), '&lt;script&gt;&quot;x&quot;&lt;/script&gt;');
  });

  it('renders code, bold and safe links', () => {
    assert.equal(inline('type `ls` now'), 'type <code>ls</code> now');
    assert.equal(inline('press **Enter**'), 'press <strong>Enter</strong>');
    assert.match(inline('[site](https://example.com)'), /<a href="https:\/\/example\.com" target="_blank" rel="noopener noreferrer">site<\/a>/);
  });

  it('leaves an unsafe link as plain text', () => {
    const out = inline('[click](javascript:alert(1))');
    assert.doesNotMatch(out, /<a /);
    assert.match(out, /javascript:alert/);
  });

  it('splits paragraphs on blank lines', () => {
    assert.equal(paragraphs('one\n\ntwo\nthree'), '<p>one</p>\n<p>two<br>three</p>');
  });

  it('safeHref allows only http, https and mailto', () => {
    assert.equal(safeHref('https://a.b'), 'https://a.b');
    assert.equal(safeHref('mailto:a@b.c'), 'mailto:a@b.c');
    assert.equal(safeHref('file:///etc/passwd'), '');
    assert.equal(safeHref('/relative'), '');
  });
});

describe('renderHtml', () => {
  const html = renderHtml(validateChecklist(JSON.parse(fs.readFileSync(EXAMPLE, 'utf8'))), 'example');

  it('renders one checkbox, one why note and one stuck button per step', () => {
    const count = (re) => (html.match(re) || []).length;
    const steps = JSON.parse(fs.readFileSync(EXAMPLE, 'utf8')).steps.length;
    assert.equal(count(/<input type="checkbox" class="tick"/g), steps);
    assert.equal(count(/role="tooltip"/g), steps);
    assert.equal(count(/class="stuck-btn"/g), steps);
  });

  it('labels every checkbox and ties each why note to its button', () => {
    for (const m of html.matchAll(/<input type="checkbox" class="tick" id="([^"]+)">/g)) {
      assert.ok(html.includes(`for="${m[1]}"`), `no label for ${m[1]}`);
    }
    for (const m of html.matchAll(/aria-describedby="([^"]+)"/g)) {
      assert.ok(html.includes(`id="${m[1]}"`), `nothing has id ${m[1]}`);
    }
  });

  it('sets a content security policy whose hashes match the inlined style and script', () => {
    const csp = /http-equiv="Content-Security-Policy" content="([^"]+)"/.exec(html)[1].replace(/&#39;/g, "'");
    assert.match(csp, /default-src 'none'/);
    const hash = (s) => `'sha256-${createHash('sha256').update(s, 'utf8').digest('base64')}'`;
    const style = /<style>([\s\S]*?)<\/style>/.exec(html)[1];
    const script = /<script>([\s\S]*?)<\/script>/.exec(html)[1];
    assert.ok(csp.includes(`style-src ${hash(style)}`));
    assert.ok(csp.includes(`script-src ${hash(script)}`));
    assert.doesNotMatch(html, / style="/);
  });

  it('escapes checklist text everywhere it lands', () => {
    const evil = '"><img src=x onerror=alert(1)>';
    const out = renderHtml(validateChecklist(sample({
      title: evil,
      summary: evil,
      source: evil,
      before: [evil],
      words: [{ word: evil, meaning: evil }],
      steps: [{
        title: evil, do: evil, why: evil, expect: evil, stuck: evil, warning: evil, group: evil,
        paste: { text: evil, into: evil },
      }],
    })), 'evil');
    assert.doesNotMatch(out, /<img/);
  });

  it('starts a new heading when the group changes', () => {
    assert.equal((html.match(/<h2 class="group">/g) || []).length, 2);
  });
});

describe('build and the command line', () => {
  it('writes the page beside the JSON by default', () => {
    const dir = tmpDir();
    const json = path.join(dir, 'My Task.json');
    fs.writeFileSync(json, JSON.stringify(sample()));
    const { out, steps } = build(json);
    assert.equal(out, path.join(dir, 'my-task.html'));
    assert.equal(steps, 2);
    assert.match(fs.readFileSync(out, 'utf8'), /data-slug="my-task"/);
  });

  it('reads a file that starts with a byte-order mark', () => {
    const dir = tmpDir();
    const json = path.join(dir, 'bom.json');
    fs.writeFileSync(json, `﻿${JSON.stringify(sample())}`);
    assert.equal(build(json).steps, 2);
  });

  it('slugOf never returns an empty name', () => {
    assert.equal(slugOf('/tmp/???.json'), 'checklist');
  });

  it('exits 2 with a plain message for a missing file, bad JSON and a bad checklist', () => {
    const dir = tmpDir();
    const run = (...args) => spawnSync(process.execPath, [SCRIPT, ...args, '--no-open'], { encoding: 'utf8' });

    let r = run(path.join(dir, 'nope.json'));
    assert.equal(r.status, 2);
    assert.match(r.stderr, /Checklist problem: no such file/);

    const bad = path.join(dir, 'bad.json');
    fs.writeFileSync(bad, '{ not json');
    r = run(bad);
    assert.equal(r.status, 2);
    assert.match(r.stderr, /not valid JSON/);

    const empty = path.join(dir, 'empty.json');
    fs.writeFileSync(empty, JSON.stringify(sample({ steps: [] })));
    r = run(empty);
    assert.equal(r.status, 2);
    assert.match(r.stderr, /at least one step/);

    r = run();
    assert.equal(r.status, 2);
    assert.match(r.stderr, /usage:/);
  });

  it('builds the example from the command line without opening a browser', () => {
    const dir = tmpDir();
    const out = path.join(dir, 'out.html');
    const r = spawnSync(process.execPath, [SCRIPT, EXAMPLE, '-o', out, '--no-open'], { encoding: 'utf8' });
    assert.equal(r.status, 0, r.stderr);
    assert.match(r.stdout, /wrote .*out\.html/);
    assert.ok(fs.existsSync(out));
  });
});
