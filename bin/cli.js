#!/usr/bin/env node
'use strict';

const path = require('path');
const {
  printHeader,
  multiSelect,
  singleSelect,
  createSpinner,
  printSummary,
  printNoSkills,
  printNoneSelected,
  printInfo,
  printWarning,
  printDivider,
  COLORS,
  RESET,
  BOLD,
} = require('../lib/ui');
const { discoverSkills } = require('../lib/discovery');
const { installSkill, uninstallSkill, getInstalledSkills, cleanupLegacy, skillsDir } = require('../lib/installer');

const PKG = require(path.join(__dirname, '..', 'package.json'));
const SKILLS_DIR = path.join(__dirname, '..', 'skills');

// ── Helpers ─────────────────────────────────────────────────────────

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// ── Scope Selection ─────────────────────────────────────────────────

async function selectScope() {
  const items = [
    {
      name: 'Global',
      description: 'Available in all projects (~/.claude/skills/)',
    },
    {
      name: 'Project',
      description: 'Available only in this project (.claude/skills/)',
    },
  ];

  const idx = await singleSelect('Where should skills be installed?', items);
  return idx === 0 ? 'global' : 'project';
}

// ── Install Flow ────────────────────────────────────────────────────

async function runInstall() {
  const skills = discoverSkills(SKILLS_DIR);
  if (skills.length === 0) {
    printNoSkills();
    process.exit(1);
  }

  // Ask where to install
  const scope = await selectScope();

  console.log('');
  printDivider();
  console.log('');

  const installed = getInstalledSkills(scope, skills.map((s) => s.name));
  const installedNames = new Set(installed.map((s) => s.name));

  // Build items for multi-select
  const items = skills.map((skill) => {
    const alreadyInstalled = installedNames.has(skill.name);
    const tag = alreadyInstalled ? ` ${COLORS.dimGray}(installed)${RESET}` : '';
    return {
      name: skill.name + tag,
      description: skill.description,
      checked: !alreadyInstalled,
      _skill: skill,
      _installed: alreadyInstalled,
    };
  });

  const scopeLabel = scope === 'global' ? 'globally' : 'for this project';
  printInfo(`Found ${BOLD}${skills.length}${RESET} skill${skills.length !== 1 ? 's' : ''} available — installing ${scopeLabel}\n`);

  const selectedIndices = await multiSelect('Select skills to install:', items);

  if (selectedIndices.length === 0) {
    printNoneSelected();
    process.exit(0);
  }

  console.log('');
  printDivider();
  console.log('');

  const results = [];
  for (const idx of selectedIndices) {
    const skill = items[idx]._skill;
    const spinner = createSpinner(`Installing ${BOLD}${skill.name}${RESET}...`);
    spinner.start();
    await sleep(300); // Brief pause for visual feedback

    const result = installSkill(skill, scope);
    results.push(result);

    if (result.ok) {
      spinner.succeed(`${BOLD}${skill.name}${RESET} installed`);
    } else {
      spinner.fail(`${BOLD}${skill.name}${RESET} failed — ${result.error}`);
    }
  }

  printSummary('install', results);

  const dir = skillsDir(scope);
  printInfo(`Skills installed to: ${COLORS.dimGray}${dir}${RESET}\n`);
}

// ── Uninstall Flow ──────────────────────────────────────────────────

async function runUninstall() {
  const skills = discoverSkills(SKILLS_DIR);
  const knownNames = skills.map((s) => s.name);

  // Ask which scope to uninstall from
  const scope = await selectScope();

  console.log('');
  printDivider();
  console.log('');

  const installed = getInstalledSkills(scope, knownNames);

  if (installed.length === 0) {
    const scopeLabel = scope === 'global' ? 'globally' : 'in this project';
    printWarning(`No LRIL skills are currently installed ${scopeLabel}.`);
    console.log('');
    process.exit(0);
  }

  printInfo(`Found ${BOLD}${installed.length}${RESET} installed skill${installed.length !== 1 ? 's' : ''}\n`);

  const items = installed.map((s) => ({
    name: s.name,
    description: s.scope === 'global' ? 'global' : 'project',
    checked: true,
  }));

  const selectedIndices = await multiSelect('Select skills to uninstall:', items);

  if (selectedIndices.length === 0) {
    printNoneSelected();
    process.exit(0);
  }

  console.log('');
  printDivider();
  console.log('');

  const results = [];
  for (const idx of selectedIndices) {
    const item = items[idx];
    const spinner = createSpinner(`Uninstalling ${BOLD}${item.name}${RESET}...`);
    spinner.start();
    await sleep(300);

    const result = uninstallSkill(item.name, scope);
    results.push(result);

    if (result.ok) {
      spinner.succeed(`${BOLD}${item.name}${RESET} removed`);
    } else {
      spinner.fail(`${BOLD}${item.name}${RESET} failed — ${result.error}`);
    }
  }

  printSummary('uninstall', results);
}

// ── Help ────────────────────────────────────────────────────────────

function printHelp() {
  console.log('');
  console.log(`  ${BOLD}Usage:${RESET}  npx lril-skills [options]`);
  console.log('');
  console.log(`  ${BOLD}Options:${RESET}`);
  console.log(`    ${COLORS.cyan}--uninstall${RESET}   Remove installed skills`);
  console.log(`    ${COLORS.cyan}--list${RESET}        List available and installed skills`);
  console.log(`    ${COLORS.cyan}--help${RESET}        Show this help message`);
  console.log(`    ${COLORS.cyan}--version${RESET}     Show version`);
  console.log('');
}

// ── List ────────────────────────────────────────────────────────────

function runList() {
  const skills = discoverSkills(SKILLS_DIR);
  const knownNames = skills.map((s) => s.name);
  const globalInstalled = getInstalledSkills('global', knownNames);
  const projectInstalled = getInstalledSkills('project', knownNames);
  const globalNames = new Set(globalInstalled.map((s) => s.name));
  const projectNames = new Set(projectInstalled.map((s) => s.name));

  console.log('');
  console.log(`  ${BOLD}Available skills:${RESET}`);
  console.log('');

  for (const skill of skills) {
    const tags = [];
    if (globalNames.has(skill.name)) tags.push('global');
    if (projectNames.has(skill.name)) tags.push('project');

    const status = tags.length > 0
      ? `${COLORS.green}● ${tags.join(', ')}${RESET}`
      : `${COLORS.gray}○ not installed${RESET}`;
    console.log(`  ${status}  ${BOLD}${skill.name}${RESET}`);
    console.log(`           ${COLORS.dimGray}${skill.description}${RESET}`);
  }
  console.log('');
}

// ── Main ────────────────────────────────────────────────────────────

async function main() {
  const args = process.argv.slice(2);

  if (args.includes('--help') || args.includes('-h')) {
    printHeader(PKG.version);
    printHelp();
    process.exit(0);
  }

  if (args.includes('--version') || args.includes('-v')) {
    console.log(PKG.version);
    process.exit(0);
  }

  printHeader(PKG.version);

  // Clean up stale registrations from old plugin-based format
  cleanupLegacy();

  if (args.includes('--list') || args.includes('-l')) {
    runList();
    process.exit(0);
  }

  if (args.includes('--uninstall') || args.includes('--remove')) {
    await runUninstall();
  } else {
    await runInstall();
  }
}

main().catch((err) => {
  console.error(`\n  Error: ${err.message}\n`);
  process.exit(1);
});
