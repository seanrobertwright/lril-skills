#!/usr/bin/env node
'use strict';

/**
 * sync-skills.js — vendor external skill repos into skills/.
 *
 * Reads sources.json, shallow-clones each upstream repo, finds every folder
 * containing a SKILL.md, and flattens it into skills/<name>/ so the existing
 * installer (lib/discovery.js) discovers it with no changes. The upstream
 * LICENSE is copied alongside each vendored skill and provenance is recorded
 * in a .vendor.json marker plus a top-level VENDORED.md manifest.
 *
 * Safety rules:
 *   - Skills you author (no .vendor.json marker) are NEVER overwritten or pruned.
 *   - A vendored skill is only overwritten/pruned by the SAME source that owns it.
 *   - Name collisions between two sources are skipped with a warning.
 *
 * Usage:  node scripts/sync-skills.js [--dry-run]
 */

const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');
const { parseFrontMatter } = require('../lib/discovery');

const ROOT = path.join(__dirname, '..');
const SKILLS_DIR = path.join(ROOT, 'skills');
const SOURCES_FILE = path.join(ROOT, 'sources.json');
const MARKER = '.vendor.json';
const DRY_RUN = process.argv.includes('--dry-run');

// ── small helpers ────────────────────────────────────────────────────

function log(msg) {
  console.log(msg);
}

function git(args, cwd) {
  return execFileSync('git', args, { cwd, encoding: 'utf-8', stdio: ['ignore', 'pipe', 'pipe'] }).trim();
}

/** Recursively collect every directory that directly contains a SKILL.md. */
function findSkillDirs(baseDir, excludeSegments) {
  const out = [];
  if (!fs.existsSync(baseDir)) return out;

  function walk(dir) {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    if (entries.some((e) => e.isFile() && e.name === 'SKILL.md')) {
      out.push(dir);
      return; // a skill dir is a leaf — don't descend into resources/scripts
    }
    for (const e of entries) {
      if (!e.isDirectory()) continue;
      if (e.name === '.git' || e.name === 'node_modules') continue;
      if (excludeSegments.includes(e.name)) continue;
      walk(path.join(dir, e.name));
    }
  }

  walk(baseDir);
  return out;
}

/** Read the front-matter `name` from a SKILL.md, falling back to the folder name. */
function skillName(skillDir) {
  const md = fs.readFileSync(path.join(skillDir, 'SKILL.md'), 'utf-8');
  const meta = parseFrontMatter(md) || {};
  const raw = (meta.name || path.basename(skillDir)).toString().trim();
  // Sanitize to a safe directory name. The name comes from an UNTRUSTED upstream
  // SKILL.md, so strip path separators and any leading/trailing dots — otherwise a
  // name like ".." would escape skills/ and a later fs.rmSync could delete the repo.
  return raw
    .toLowerCase()
    .replace(/[^a-z0-9._-]+/g, '-')
    .replace(/^[.-]+|[.-]+$/g, '');
}

/** True only if `name` is a safe, single-segment directory inside SKILLS_DIR. */
function isSafeSkillName(name) {
  if (!name || name === '.' || name === '..') return false;
  if (name.includes('/') || name.includes('\\')) return false;
  const dest = path.join(SKILLS_DIR, name);
  const rel = path.relative(SKILLS_DIR, dest);
  return rel !== '' && !rel.startsWith('..') && !path.isAbsolute(rel);
}

/** Find the LICENSE file at a repo root (case/extension insensitive). */
function findLicense(repoRoot) {
  const entries = fs.readdirSync(repoRoot);
  return entries.find((f) => /^licen[cs]e(\.|$)/i.test(f) || /^copying(\.|$)/i.test(f)) || null;
}

function readMarker(dir) {
  const p = path.join(dir, MARKER);
  if (!fs.existsSync(p)) return null;
  try {
    return JSON.parse(fs.readFileSync(p, 'utf-8'));
  } catch {
    return null;
  }
}

// ── main ─────────────────────────────────────────────────────────────

function main() {
  if (!fs.existsSync(SOURCES_FILE)) {
    console.error(`No sources.json found at ${SOURCES_FILE}`);
    process.exit(1);
  }

  const { sources } = JSON.parse(fs.readFileSync(SOURCES_FILE, 'utf-8'));
  if (!Array.isArray(sources) || sources.length === 0) {
    log('sources.json has no sources — nothing to do.');
    return;
  }

  fs.mkdirSync(SKILLS_DIR, { recursive: true });

  const vendored = []; // { name, source, repo, path, commit, license }
  const ownedNames = new Set(); // skills authored here (no marker)
  for (const entry of fs.readdirSync(SKILLS_DIR, { withFileTypes: true })) {
    if (entry.isDirectory() && !readMarker(path.join(SKILLS_DIR, entry.name))) {
      ownedNames.add(entry.name);
    }
  }

  for (const src of sources) {
    log(`\n── ${src.name} ─────────────────────────────────────────`);
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'skillsync-'));
    try {
      git(['clone', '--depth', '1', '--branch', src.branch || 'main', src.repo, tmp]);
      const commit = git(['rev-parse', 'HEAD'], tmp);
      const licenseFile = findLicense(tmp);
      if (!licenseFile) {
        log(`  ⚠ no LICENSE found in ${src.name} — skipping source (cannot redistribute safely)`);
        continue;
      }

      const base = path.join(tmp, src.skillsDir || 'skills');
      const skillDirs = findSkillDirs(base, src.exclude || []);
      log(`  found ${skillDirs.length} skill(s) @ ${commit.slice(0, 8)}`);

      for (const skillDir of skillDirs) {
        const name = skillName(skillDir);
        if (!isSafeSkillName(name)) {
          const where = path.relative(tmp, skillDir).split(path.sep).join('/');
          log(`  ⚠  unsafe/empty skill name from ${where} — skipping`);
          continue;
        }
        const dest = path.join(SKILLS_DIR, name);
        const existing = readMarker(dest);

        if (ownedNames.has(name)) {
          log(`  ⏭  ${name} — owned by this repo, not overwriting`);
          continue;
        }
        if (existing && existing.source !== src.name) {
          log(`  ⚠  ${name} — collision (already vendored from ${existing.source}), skipping`);
          continue;
        }

        const marker = {
          source: src.name,
          repo: src.repo,
          branch: src.branch || 'main',
          path: path.relative(tmp, skillDir).split(path.sep).join('/'),
          commit,
          license: src.license || 'see LICENSE',
          syncedAt: process.env.SYNC_TIMESTAMP || null,
        };

        if (!DRY_RUN) {
          fs.rmSync(dest, { recursive: true, force: true });
          fs.cpSync(skillDir, dest, { recursive: true });
          fs.copyFileSync(path.join(tmp, licenseFile), path.join(dest, 'LICENSE'));
          fs.writeFileSync(path.join(dest, MARKER), JSON.stringify(marker, null, 2) + '\n');
        }
        vendored.push({ name, ...marker });
        log(`  ✓  ${name}`);
      }

      // prune: vendored skills from THIS source that no longer exist upstream
      const seen = new Set(vendored.filter((v) => v.source === src.name).map((v) => v.name));
      for (const entry of fs.readdirSync(SKILLS_DIR, { withFileTypes: true })) {
        if (!entry.isDirectory()) continue;
        const m = readMarker(path.join(SKILLS_DIR, entry.name));
        if (m && m.source === src.name && !seen.has(entry.name)) {
          log(`  🗑  ${entry.name} — removed upstream, pruning`);
          if (!DRY_RUN) fs.rmSync(path.join(SKILLS_DIR, entry.name), { recursive: true, force: true });
        }
      }
    } finally {
      fs.rmSync(tmp, { recursive: true, force: true });
    }
  }

  writeManifest(vendored);
  log(`\nDone. ${vendored.length} vendored skill(s)${DRY_RUN ? ' (dry-run, nothing written)' : ''}.`);
}

/** Regenerate VENDORED.md from the .vendor.json markers currently on disk. */
function writeManifest(vendoredThisRun) {
  const rows = [];
  for (const entry of fs.readdirSync(SKILLS_DIR, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    const m = readMarker(path.join(SKILLS_DIR, entry.name));
    if (m) rows.push({ name: entry.name, ...m });
  }
  rows.sort((a, b) => a.name.localeCompare(b.name));

  const lines = [
    '# Vendored skills',
    '',
    'These skills are mirrored from upstream repos by `scripts/sync-skills.js`',
    '(configured in `sources.json`). Do not edit them by hand — changes are',
    'overwritten on the next sync. Each retains its upstream `LICENSE`.',
    '',
    '| Skill | Source | Commit | License |',
    '|-------|--------|--------|---------|',
    ...rows.map(
      (r) =>
        `| \`${r.name}\` | [${r.source}](${r.repo.replace(/\.git$/, '')}) | \`${(r.commit || '').slice(0, 8)}\` | ${r.license} |`
    ),
    '',
  ];

  if (!DRY_RUN) fs.writeFileSync(path.join(ROOT, 'VENDORED.md'), lines.join('\n'));
}

main();
