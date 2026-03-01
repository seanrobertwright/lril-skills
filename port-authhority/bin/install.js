#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const os = require('os');

const PKG = require(path.join(__dirname, '..', 'package.json'));
const PLUGIN_NAME = PKG.name;
const VERSION = PKG.version;
const PLUGIN_KEY = `${PLUGIN_NAME}@standalone`;

const CLAUDE_DIR = path.join(os.homedir(), '.claude');
const PLUGINS_DIR = path.join(CLAUDE_DIR, 'plugins');
const INSTALLED_JSON = path.join(PLUGINS_DIR, 'installed_plugins.json');
const SETTINGS_JSON = path.join(CLAUDE_DIR, 'settings.json');
const CACHE_DIR = path.join(PLUGINS_DIR, 'cache', 'standalone', PLUGIN_NAME, VERSION);
const SKILL_TARGET = path.join(CACHE_DIR, 'skills', PLUGIN_NAME);
const PLUGIN_JSON_DIR = path.join(CACHE_DIR, '.claude-plugin');
const SKILL_SOURCE = path.join(__dirname, '..', 'skill');

// ── Helpers ──────────────────────────────────────────────────────────

function log(msg) {
  console.log(`  ${msg}`);
}

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

// ── Install ──────────────────────────────────────────────────────────

function install() {
  console.log(`\nInstalling ${PLUGIN_NAME} v${VERSION}...\n`);

  // 1. Copy skill files
  log('Copying skill files...');
  copyRecursive(SKILL_SOURCE, SKILL_TARGET);
  log(`  → ${SKILL_TARGET}`);

  // 2. Write plugin.json
  log('Writing plugin manifest...');
  writeJSON(path.join(PLUGIN_JSON_DIR, 'plugin.json'), {
    name: PLUGIN_NAME,
    description: PKG.description,
    version: VERSION,
  });
  log(`  → ${PLUGIN_JSON_DIR}/plugin.json`);

  // 3. Update installed_plugins.json
  log('Registering plugin...');
  const installed = readJSON(INSTALLED_JSON) || { version: 2, plugins: {} };
  if (!installed.plugins) installed.plugins = {};
  installed.plugins[PLUGIN_KEY] = {
    version: VERSION,
    type: 'standalone',
    installPath: CACHE_DIR,
  };
  writeJSON(INSTALLED_JSON, installed);
  log(`  → ${INSTALLED_JSON}`);

  // 4. Update settings.json
  log('Enabling plugin in settings...');
  const settings = readJSON(SETTINGS_JSON) || {};
  if (!settings.enabledPlugins) settings.enabledPlugins = {};
  settings.enabledPlugins[PLUGIN_KEY] = true;
  writeJSON(SETTINGS_JSON, settings);
  log(`  → ${SETTINGS_JSON}`);

  console.log(`\n  Done! ${PLUGIN_NAME} is now available in Claude Code.\n`);
}

// ── Uninstall ────────────────────────────────────────────────────────

function uninstall() {
  console.log(`\nUninstalling ${PLUGIN_NAME}...\n`);

  // 1. Remove cached files
  log('Removing skill files...');
  removeRecursive(CACHE_DIR);

  // Clean up empty parent dirs
  const standaloneDir = path.join(PLUGINS_DIR, 'cache', 'standalone', PLUGIN_NAME);
  try {
    if (fs.existsSync(standaloneDir) && fs.readdirSync(standaloneDir).length === 0) {
      fs.rmdirSync(standaloneDir);
    }
  } catch { /* ignore */ }

  // 2. Remove from installed_plugins.json
  log('Removing plugin registration...');
  const installed = readJSON(INSTALLED_JSON);
  if (installed && installed.plugins) {
    delete installed.plugins[PLUGIN_KEY];
    writeJSON(INSTALLED_JSON, installed);
  }

  // 3. Remove from settings.json
  log('Removing from settings...');
  const settings = readJSON(SETTINGS_JSON);
  if (settings && settings.enabledPlugins) {
    delete settings.enabledPlugins[PLUGIN_KEY];
    writeJSON(SETTINGS_JSON, settings);
  }

  console.log(`\n  Done! ${PLUGIN_NAME} has been removed.\n`);
}

// ── Main ─────────────────────────────────────────────────────────────

const args = process.argv.slice(2);
if (args.includes('--uninstall') || args.includes('--remove')) {
  uninstall();
} else {
  install();
}
