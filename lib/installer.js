'use strict';

const fs = require('fs');
const path = require('path');
const os = require('os');

// ── Constants ───────────────────────────────────────────────────────

const CLAUDE_DIR = path.join(os.homedir(), '.claude');
const GLOBAL_SKILLS_DIR = path.join(CLAUDE_DIR, 'skills');

// Legacy plugin constants (for cleanup only)
const LEGACY_PLUGIN_KEY = 'lril-skills@lril-skills';
const PLUGINS_DIR = path.join(CLAUDE_DIR, 'plugins');
const INSTALLED_JSON = path.join(PLUGINS_DIR, 'installed_plugins.json');
const SETTINGS_JSON = path.join(CLAUDE_DIR, 'settings.json');
const KNOWN_MARKETPLACES_JSON = path.join(PLUGINS_DIR, 'known_marketplaces.json');

// ── Helpers ─────────────────────────────────────────────────────────

function readJSON(filepath) {
  try {
    return JSON.parse(fs.readFileSync(filepath, 'utf-8'));
  } catch {
    return null;
  }
}

function writeJSON(filepath, data) {
  fs.mkdirSync(path.dirname(filepath), { recursive: true });
  fs.writeFileSync(filepath, JSON.stringify(data, null, 2) + '\n', 'utf-8');
}

function copyRecursive(src, dest) {
  fs.mkdirSync(dest, { recursive: true });
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);
    if (entry.isDirectory()) {
      copyRecursive(srcPath, destPath);
    } else {
      fs.copyFileSync(srcPath, destPath);
    }
  }
}

function removeRecursive(dir) {
  if (!fs.existsSync(dir)) return;
  fs.rmSync(dir, { recursive: true, force: true });
}

/**
 * Get the skills directory for the given scope.
 * @param {'global'|'project'} scope
 * @returns {string}
 */
function skillsDir(scope) {
  if (scope === 'project') {
    return path.join(process.cwd(), '.claude', 'skills');
  }
  return GLOBAL_SKILLS_DIR;
}

// ── Install ─────────────────────────────────────────────────────────

/**
 * Install a single skill by copying it to the Claude Code skills directory.
 * Claude Code auto-detects SKILL.md files in ~/.claude/skills/ (global)
 * and .claude/skills/ (project-scoped).
 *
 * @param {object} skill - { name, description, dir, meta }
 * @param {'global'|'project'} scope - Installation scope
 * @returns {{ ok: boolean, name: string, error?: string }}
 */
function installSkill(skill, scope) {
  try {
    const targetDir = path.join(skillsDir(scope), skill.name);
    copyRecursive(skill.dir, targetDir);
    return { ok: true, name: skill.name };
  } catch (err) {
    return { ok: false, name: skill.name, error: err.message };
  }
}

// ── Uninstall ───────────────────────────────────────────────────────

/**
 * Uninstall a single skill from the skills directory.
 * @param {string} name - Skill name
 * @param {'global'|'project'} scope - Installation scope
 * @returns {{ ok: boolean, name: string, error?: string }}
 */
function uninstallSkill(name, scope) {
  try {
    const dir = path.join(skillsDir(scope), name);
    removeRecursive(dir);
    return { ok: true, name };
  } catch (err) {
    return { ok: false, name, error: err.message };
  }
}

// ── Query ───────────────────────────────────────────────────────────

/**
 * Get list of currently installed lril skills for a given scope.
 * @param {'global'|'project'} scope
 * @param {Array<string>} knownSkillNames - Names of skills this installer manages
 * @returns {Array<{name: string, scope: string}>}
 */
function getInstalledSkills(scope, knownSkillNames) {
  const dir = skillsDir(scope);
  if (!fs.existsSync(dir)) return [];

  const knownSet = new Set(knownSkillNames);
  const skills = [];

  try {
    for (const name of fs.readdirSync(dir)) {
      // Only report skills that this installer manages
      if (!knownSet.has(name)) continue;
      const skillMd = path.join(dir, name, 'SKILL.md');
      if (fs.existsSync(skillMd)) {
        skills.push({ name, scope });
      }
    }
  } catch { /* ignore */ }

  return skills;
}

// ── Legacy Cleanup ──────────────────────────────────────────────────

/**
 * Clean up old plugin-based installations and standalone registrations.
 * Migrates to the simpler skills directory approach.
 */
function cleanupLegacy() {
  const installed = readJSON(INSTALLED_JSON);
  const settings = readJSON(SETTINGS_JSON);
  let installedChanged = false;
  let settingsChanged = false;

  if (installed && installed.plugins) {
    // Remove old standalone entries
    for (const key of Object.keys(installed.plugins)) {
      if (key.endsWith('@standalone')) {
        const info = installed.plugins[key];
        if (info && !Array.isArray(info) && info.type === 'standalone') {
          if (info.installPath) removeRecursive(info.installPath);
          delete installed.plugins[key];
          installedChanged = true;
        }
      }
    }

    // Remove old lril-skills plugin entry
    if (installed.plugins[LEGACY_PLUGIN_KEY]) {
      const entry = installed.plugins[LEGACY_PLUGIN_KEY];
      const info = Array.isArray(entry) ? entry[0] : entry;
      if (info && info.installPath) removeRecursive(info.installPath);
      delete installed.plugins[LEGACY_PLUGIN_KEY];
      installedChanged = true;
    }
  }

  if (settings && settings.enabledPlugins) {
    // Remove orphaned standalone entries
    for (const key of Object.keys(settings.enabledPlugins)) {
      if (key.endsWith('@standalone')) {
        delete settings.enabledPlugins[key];
        settingsChanged = true;
      }
    }

    // Remove old lril-skills plugin entry
    if (settings.enabledPlugins[LEGACY_PLUGIN_KEY]) {
      delete settings.enabledPlugins[LEGACY_PLUGIN_KEY];
      settingsChanged = true;
    }
  }

  if (installedChanged) writeJSON(INSTALLED_JSON, installed);
  if (settingsChanged) writeJSON(SETTINGS_JSON, settings);

  // Remove old marketplace registration
  const known = readJSON(KNOWN_MARKETPLACES_JSON);
  if (known && known['lril-skills']) {
    delete known['lril-skills'];
    writeJSON(KNOWN_MARKETPLACES_JSON, known);
  }

  // Remove old cache directory
  const oldCache = path.join(PLUGINS_DIR, 'cache', 'lril-skills');
  removeRecursive(oldCache);

  // Remove old marketplace directory
  const oldMarketplace = path.join(PLUGINS_DIR, 'marketplaces', 'lril-skills');
  removeRecursive(oldMarketplace);
}

module.exports = {
  installSkill,
  uninstallSkill,
  getInstalledSkills,
  cleanupLegacy,
  skillsDir,
  CLAUDE_DIR,
};
