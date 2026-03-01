'use strict';

const fs = require('fs');
const path = require('path');
const os = require('os');

// ── Paths ───────────────────────────────────────────────────────────

const CLAUDE_DIR = path.join(os.homedir(), '.claude');
const PLUGINS_DIR = path.join(CLAUDE_DIR, 'plugins');
const INSTALLED_JSON = path.join(PLUGINS_DIR, 'installed_plugins.json');
const SETTINGS_JSON = path.join(CLAUDE_DIR, 'settings.json');

function cacheDir(name, version) {
  return path.join(PLUGINS_DIR, 'cache', 'standalone', name, version);
}

function pluginKey(name) {
  return `${name}@standalone`;
}

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

// ── Install ─────────────────────────────────────────────────────────

/**
 * Install a single skill.
 * @param {object} skill - { name, description, dir, meta }
 * @param {string} version - Version string from package.json
 * @returns {{ ok: boolean, name: string, error?: string }}
 */
function installSkill(skill, version) {
  try {
    const cache = cacheDir(skill.name, version);
    const skillTarget = path.join(cache, 'skills', skill.name);
    const pluginJsonDir = path.join(cache, '.claude-plugin');
    const key = pluginKey(skill.name);

    // 1. Copy skill files
    copyRecursive(skill.dir, skillTarget);

    // 2. Write plugin.json manifest
    writeJSON(path.join(pluginJsonDir, 'plugin.json'), {
      name: skill.name,
      description: skill.description,
      version,
    });

    // 3. Register in installed_plugins.json
    const installed = readJSON(INSTALLED_JSON) || { version: 2, plugins: {} };
    if (!installed.plugins) installed.plugins = {};
    installed.plugins[key] = {
      version,
      type: 'standalone',
      installPath: cache,
    };
    writeJSON(INSTALLED_JSON, installed);

    // 4. Enable in settings.json
    const settings = readJSON(SETTINGS_JSON) || {};
    if (!settings.enabledPlugins) settings.enabledPlugins = {};
    settings.enabledPlugins[key] = true;
    writeJSON(SETTINGS_JSON, settings);

    return { ok: true, name: skill.name };
  } catch (err) {
    return { ok: false, name: skill.name, error: err.message };
  }
}

// ── Uninstall ───────────────────────────────────────────────────────

/**
 * Uninstall a single skill.
 * @param {string} name - Skill name
 * @param {string} version - Version to remove
 * @returns {{ ok: boolean, name: string, error?: string }}
 */
function uninstallSkill(name, version) {
  try {
    const cache = cacheDir(name, version);
    const key = pluginKey(name);

    // 1. Remove cached files
    removeRecursive(cache);

    // Clean up empty parent dir
    const parentDir = path.join(PLUGINS_DIR, 'cache', 'standalone', name);
    try {
      if (fs.existsSync(parentDir) && fs.readdirSync(parentDir).length === 0) {
        fs.rmdirSync(parentDir);
      }
    } catch { /* ignore */ }

    // 2. Remove from installed_plugins.json
    const installed = readJSON(INSTALLED_JSON);
    if (installed && installed.plugins) {
      delete installed.plugins[key];
      writeJSON(INSTALLED_JSON, installed);
    }

    // 3. Remove from settings.json
    const settings = readJSON(SETTINGS_JSON);
    if (settings && settings.enabledPlugins) {
      delete settings.enabledPlugins[key];
      writeJSON(SETTINGS_JSON, settings);
    }

    return { ok: true, name };
  } catch (err) {
    return { ok: false, name, error: err.message };
  }
}

// ── Query ───────────────────────────────────────────────────────────

/**
 * Get list of currently installed lril skills.
 * @returns {Array<{name: string, version: string}>}
 */
function getInstalledSkills() {
  const installed = readJSON(INSTALLED_JSON);
  if (!installed || !installed.plugins) return [];

  const skills = [];
  for (const [key, info] of Object.entries(installed.plugins)) {
    if (key.endsWith('@standalone') && info.type === 'standalone') {
      skills.push({
        name: key.replace(/@standalone$/, ''),
        version: info.version,
      });
    }
  }
  return skills;
}

module.exports = {
  installSkill,
  uninstallSkill,
  getInstalledSkills,
  CLAUDE_DIR,
  PLUGINS_DIR,
};
