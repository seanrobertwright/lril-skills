'use strict';

const fs = require('fs');
const path = require('path');
const os = require('os');

// ── Constants ───────────────────────────────────────────────────────

const MARKETPLACE = 'lril-skills';
const PLUGIN_NAME = 'lril-skills';
const PLUGIN_KEY = `${PLUGIN_NAME}@${MARKETPLACE}`;

const CLAUDE_DIR = path.join(os.homedir(), '.claude');
const PLUGINS_DIR = path.join(CLAUDE_DIR, 'plugins');
const INSTALLED_JSON = path.join(PLUGINS_DIR, 'installed_plugins.json');
const SETTINGS_JSON = path.join(CLAUDE_DIR, 'settings.json');

function cacheDir(version) {
  return path.join(PLUGINS_DIR, 'cache', MARKETPLACE, PLUGIN_NAME, version);
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
 * Install a single skill into the lril-skills plugin cache.
 * All skills share a single plugin registration.
 * @param {object} skill - { name, description, dir, meta }
 * @param {string} version - Version string from package.json
 * @returns {{ ok: boolean, name: string, error?: string }}
 */
function installSkill(skill, version) {
  try {
    const cache = cacheDir(version);
    const skillTarget = path.join(cache, 'skills', skill.name);

    // 1. Copy skill files
    copyRecursive(skill.dir, skillTarget);

    // 2. Write plugin.json manifest (shared across all skills)
    const pluginJsonDir = path.join(cache, '.claude-plugin');
    writeJSON(path.join(pluginJsonDir, 'plugin.json'), {
      name: PLUGIN_NAME,
      description: 'LRIL Claude Code skills collection',
      version,
    });

    // 3. Register plugin in installed_plugins.json (array format)
    const now = new Date().toISOString();
    const installed = readJSON(INSTALLED_JSON) || { version: 2, plugins: {} };
    if (!installed.plugins) installed.plugins = {};

    // Use array format matching Claude Code's expected structure
    const existingEntry = Array.isArray(installed.plugins[PLUGIN_KEY])
      ? installed.plugins[PLUGIN_KEY][0]
      : null;

    installed.plugins[PLUGIN_KEY] = [
      {
        scope: 'user',
        installPath: cache,
        version,
        installedAt: existingEntry ? existingEntry.installedAt : now,
        lastUpdated: now,
      },
    ];
    writeJSON(INSTALLED_JSON, installed);

    // 4. Enable in settings.json
    const settings = readJSON(SETTINGS_JSON) || {};
    if (!settings.enabledPlugins) settings.enabledPlugins = {};
    settings.enabledPlugins[PLUGIN_KEY] = true;
    writeJSON(SETTINGS_JSON, settings);

    return { ok: true, name: skill.name };
  } catch (err) {
    return { ok: false, name: skill.name, error: err.message };
  }
}

// ── Uninstall ───────────────────────────────────────────────────────

/**
 * Uninstall a single skill from the plugin cache.
 * @param {string} name - Skill name
 * @param {string} version - Version to remove
 * @returns {{ ok: boolean, name: string, error?: string }}
 */
function uninstallSkill(name, version) {
  try {
    const cache = cacheDir(version);
    const skillDir = path.join(cache, 'skills', name);

    // 1. Remove this skill's directory
    removeRecursive(skillDir);

    // 2. Check if any skills remain
    const skillsDir = path.join(cache, 'skills');
    let remainingSkills = [];
    try {
      remainingSkills = fs.readdirSync(skillsDir);
    } catch { /* dir may not exist */ }

    // 3. If no skills remain, clean up the entire plugin registration
    if (remainingSkills.length === 0) {
      removeRecursive(cache);

      // Clean up empty parent dirs
      const marketplaceDir = path.join(PLUGINS_DIR, 'cache', MARKETPLACE, PLUGIN_NAME);
      try {
        if (fs.existsSync(marketplaceDir) && fs.readdirSync(marketplaceDir).length === 0) {
          fs.rmdirSync(marketplaceDir);
        }
      } catch { /* ignore */ }
      const topDir = path.join(PLUGINS_DIR, 'cache', MARKETPLACE);
      try {
        if (fs.existsSync(topDir) && fs.readdirSync(topDir).length === 0) {
          fs.rmdirSync(topDir);
        }
      } catch { /* ignore */ }

      // Remove from installed_plugins.json
      const installed = readJSON(INSTALLED_JSON);
      if (installed && installed.plugins) {
        delete installed.plugins[PLUGIN_KEY];
        writeJSON(INSTALLED_JSON, installed);
      }

      // Remove from settings.json
      const settings = readJSON(SETTINGS_JSON);
      if (settings && settings.enabledPlugins) {
        delete settings.enabledPlugins[PLUGIN_KEY];
        writeJSON(SETTINGS_JSON, settings);
      }
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

  const entry = installed.plugins[PLUGIN_KEY];
  if (!entry) return [];

  // Support both array and object formats
  const info = Array.isArray(entry) ? entry[0] : entry;
  if (!info || !info.installPath) return [];

  // Scan the skills directory in the cache
  const skillsDir = path.join(info.installPath, 'skills');
  if (!fs.existsSync(skillsDir)) return [];

  const skills = [];
  try {
    for (const name of fs.readdirSync(skillsDir)) {
      const skillMd = path.join(skillsDir, name, 'SKILL.md');
      if (fs.existsSync(skillMd)) {
        skills.push({ name, version: info.version });
      }
    }
  } catch { /* ignore */ }

  return skills;
}

/**
 * Clean up stale registrations from the old standalone format.
 */
function cleanupLegacy() {
  const installed = readJSON(INSTALLED_JSON);
  const settings = readJSON(SETTINGS_JSON);
  let installedChanged = false;
  let settingsChanged = false;

  // Remove old standalone entries from installed_plugins.json
  if (installed && installed.plugins) {
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
  }

  // Remove orphaned @standalone entries from settings.json
  if (settings && settings.enabledPlugins) {
    for (const key of Object.keys(settings.enabledPlugins)) {
      if (key.endsWith('@standalone')) {
        delete settings.enabledPlugins[key];
        settingsChanged = true;
      }
    }
  }

  if (installedChanged) writeJSON(INSTALLED_JSON, installed);
  if (settingsChanged) writeJSON(SETTINGS_JSON, settings);
}

module.exports = {
  installSkill,
  uninstallSkill,
  getInstalledSkills,
  cleanupLegacy,
  PLUGIN_KEY,
  CLAUDE_DIR,
  PLUGINS_DIR,
};
