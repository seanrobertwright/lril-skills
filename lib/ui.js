'use strict';

const readline = require('readline');

// ── ANSI Color Helpers ──────────────────────────────────────────────

const ESC = '\x1b[';
const RESET = `${ESC}0m`;
const BOLD = `${ESC}1m`;
const DIM = `${ESC}2m`;
const ITALIC = `${ESC}3m`;
const UNDERLINE = `${ESC}4m`;

const fg = (r, g, b) => `${ESC}38;2;${r};${g};${b}m`;
const bg = (r, g, b) => `${ESC}48;2;${r};${g};${b}m`;

const COLORS = {
  cyan:    fg(0, 220, 255),
  blue:    fg(80, 140, 255),
  purple:  fg(160, 100, 255),
  magenta: fg(220, 80, 220),
  pink:    fg(255, 100, 150),
  green:   fg(80, 250, 123),
  yellow:  fg(255, 220, 80),
  red:     fg(255, 85, 85),
  orange:  fg(255, 160, 50),
  white:   fg(255, 255, 255),
  gray:    fg(130, 130, 150),
  dimGray: fg(80, 80, 100),
};

// Gradient palette for the ASCII header
const GRADIENT = [
  [0, 200, 255],   // cyan
  [40, 170, 255],  // light blue
  [80, 140, 255],  // blue
  [120, 120, 255], // blue-purple
  [160, 100, 255], // purple
  [200, 80, 240],  // magenta
  [240, 70, 200],  // pink
];

function gradientText(text, colors) {
  if (text.length === 0) return '';
  const result = [];
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (ch === ' ') {
      result.push(' ');
      continue;
    }
    const t = text.length > 1 ? i / (text.length - 1) : 0;
    const segLen = colors.length - 1;
    const seg = Math.min(Math.floor(t * segLen), segLen - 1);
    const segT = (t * segLen) - seg;
    const c1 = colors[seg];
    const c2 = colors[seg + 1] || c1;
    const r = Math.round(c1[0] + (c2[0] - c1[0]) * segT);
    const g = Math.round(c1[1] + (c2[1] - c1[1]) * segT);
    const b = Math.round(c1[2] + (c2[2] - c1[2]) * segT);
    result.push(`${fg(r, g, b)}${ch}`);
  }
  return result.join('') + RESET;
}

// ── ASCII Header ────────────────────────────────────────────────────

const HEADER_ART = [
  '  ██╗     ██████╗  ██╗██╗           ███████╗██╗  ██╗██╗██╗     ██╗     ███████╗',
  '  ██║     ██╔══██╗ ██║██║           ██╔════╝██║ ██╔╝██║██║     ██║     ██╔════╝',
  '  ██║     ██████╔╝ ██║██║     █████╗███████╗█████╔╝ ██║██║     ██║     ███████╗',
  '  ██║     ██╔══██╗ ██║██║     ╚════╝╚════██║██╔═██╗ ██║██║     ██║     ╚════██║',
  '  ███████╗██║  ██║ ██║███████╗      ███████║██║  ██╗██║███████╗███████╗███████║',
  '  ╚══════╝╚═╝  ╚═╝ ╚═╝╚══════╝      ╚══════╝╚═╝  ╚═╝╚═╝╚══════╝╚══════╝╚══════╝',
];

function printHeader(version) {
  console.log('');
  for (const line of HEADER_ART) {
    console.log(gradientText(line, GRADIENT));
  }
  const tagline = '  Claude Code Skills Installer';
  const ver = `v${version}`;
  console.log('');
  console.log(`  ${COLORS.gray}${tagline}${RESET}  ${COLORS.dimGray}${ver}${RESET}`);
  console.log(`  ${COLORS.dimGray}${'─'.repeat(56)}${RESET}`);
  console.log('');
}

// ── Interactive Multi-Select ────────────────────────────────────────

const CHECKBOX_ON  = `${COLORS.green}◉${RESET}`;
const CHECKBOX_OFF = `${COLORS.gray}○${RESET}`;
const POINTER      = `${COLORS.cyan}❯${RESET}`;
const POINTER_NONE = ' ';

/**
 * Show an interactive multi-select list.
 * @param {string} title - Prompt text
 * @param {Array<{name: string, description: string, checked?: boolean}>} items
 * @returns {Promise<number[]>} Selected indices
 */
async function multiSelect(title, items) {
  return new Promise((resolve) => {
    const selected = items.map((item) => item.checked || false);
    let cursor = 0;

    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
      terminal: false,
    });

    // Enable raw mode for keypress detection
    if (process.stdin.isTTY) {
      process.stdin.setRawMode(true);
    }
    process.stdin.resume();

    function render() {
      // Move cursor up and clear (except first render)
      const totalLines = items.length + 4;
      process.stdout.write(`${ESC}${totalLines}A${ESC}J`);
      draw();
    }

    function draw() {
      console.log(`  ${BOLD}${COLORS.white}${title}${RESET}`);
      console.log(`  ${COLORS.dimGray}↑/↓ navigate  ⎵ toggle  a select all  enter confirm${RESET}`);
      console.log('');

      for (let i = 0; i < items.length; i++) {
        const ptr = i === cursor ? POINTER : POINTER_NONE;
        const chk = selected[i] ? CHECKBOX_ON : CHECKBOX_OFF;
        const nameColor = i === cursor ? COLORS.white : COLORS.gray;
        const descColor = COLORS.dimGray;
        const name = `${BOLD}${nameColor}${items[i].name}${RESET}`;
        const desc = items[i].description ? `  ${descColor}${items[i].description}${RESET}` : '';
        console.log(`  ${ptr} ${chk} ${name}${desc}`);
      }
      console.log('');
    }

    // Initial draw
    draw();

    process.stdin.on('data', (data) => {
      const key = data.toString();

      // Enter
      if (key === '\r' || key === '\n') {
        cleanup();
        const indices = [];
        for (let i = 0; i < selected.length; i++) {
          if (selected[i]) indices.push(i);
        }
        resolve(indices);
        return;
      }

      // Space - toggle
      if (key === ' ') {
        selected[cursor] = !selected[cursor];
        render();
        return;
      }

      // 'a' - toggle all
      if (key === 'a' || key === 'A') {
        const allSelected = selected.every(Boolean);
        for (let i = 0; i < selected.length; i++) {
          selected[i] = !allSelected;
        }
        render();
        return;
      }

      // Ctrl+C or q
      if (key === '\x03' || key === 'q') {
        cleanup();
        process.exit(0);
      }

      // Arrow keys (escape sequences)
      if (key === '\x1b[A' || key === 'k') {
        // Up
        cursor = cursor > 0 ? cursor - 1 : items.length - 1;
        render();
        return;
      }
      if (key === '\x1b[B' || key === 'j') {
        // Down
        cursor = cursor < items.length - 1 ? cursor + 1 : 0;
        render();
        return;
      }
    });

    function cleanup() {
      if (process.stdin.isTTY) {
        process.stdin.setRawMode(false);
      }
      process.stdin.pause();
      process.stdin.removeAllListeners('data');
      rl.close();
    }
  });
}

// ── Progress & Status ───────────────────────────────────────────────

const SPINNER_FRAMES = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'];

function createSpinner(text) {
  let frame = 0;
  let interval = null;

  return {
    start() {
      interval = setInterval(() => {
        const spinner = `${COLORS.cyan}${SPINNER_FRAMES[frame]}${RESET}`;
        process.stdout.write(`\r  ${spinner} ${COLORS.gray}${text}${RESET}${ESC}K`);
        frame = (frame + 1) % SPINNER_FRAMES.length;
      }, 80);
    },
    succeed(msg) {
      clearInterval(interval);
      process.stdout.write(`\r  ${COLORS.green}✔${RESET} ${msg || text}${ESC}K\n`);
    },
    fail(msg) {
      clearInterval(interval);
      process.stdout.write(`\r  ${COLORS.red}✖${RESET} ${msg || text}${ESC}K\n`);
    },
  };
}

function printSuccess(msg) {
  console.log(`  ${COLORS.green}✔${RESET} ${msg}`);
}

function printError(msg) {
  console.log(`  ${COLORS.red}✖${RESET} ${msg}`);
}

function printInfo(msg) {
  console.log(`  ${COLORS.cyan}ℹ${RESET} ${msg}`);
}

function printWarning(msg) {
  console.log(`  ${COLORS.yellow}⚠${RESET} ${msg}`);
}

function printDivider() {
  console.log(`  ${COLORS.dimGray}${'─'.repeat(56)}${RESET}`);
}

// ── Summary Box ─────────────────────────────────────────────────────

function printSummary(action, results) {
  console.log('');
  printDivider();
  console.log('');
  const actionPast = action === 'install' ? 'Installed' : 'Uninstalled';
  const color = action === 'install' ? COLORS.green : COLORS.orange;

  const succeeded = results.filter((r) => r.ok);
  const failed = results.filter((r) => !r.ok);

  if (succeeded.length > 0) {
    console.log(`  ${color}${BOLD}${actionPast} ${succeeded.length} skill${succeeded.length !== 1 ? 's' : ''}:${RESET}`);
    for (const r of succeeded) {
      console.log(`  ${COLORS.green}✔${RESET} ${BOLD}${r.name}${RESET}`);
    }
  }

  if (failed.length > 0) {
    console.log('');
    console.log(`  ${COLORS.red}${BOLD}Failed ${failed.length}:${RESET}`);
    for (const r of failed) {
      console.log(`  ${COLORS.red}✖${RESET} ${BOLD}${r.name}${RESET} — ${COLORS.dimGray}${r.error}${RESET}`);
    }
  }

  console.log('');
  if (action === 'install' && succeeded.length > 0) {
    console.log(`  ${COLORS.gray}Restart Claude Code to activate new skills.${RESET}`);
  }
  console.log('');
}

function printNoSkills() {
  console.log(`  ${COLORS.yellow}No skills found to install.${RESET}`);
  console.log(`  ${COLORS.dimGray}Expected SKILL.md files in skills/ subdirectories.${RESET}`);
  console.log('');
}

function printNoneSelected() {
  console.log(`  ${COLORS.gray}No skills selected. Nothing to do.${RESET}`);
  console.log('');
}

module.exports = {
  COLORS,
  RESET,
  BOLD,
  DIM,
  printHeader,
  multiSelect,
  createSpinner,
  printSuccess,
  printError,
  printInfo,
  printWarning,
  printDivider,
  printSummary,
  printNoSkills,
  printNoneSelected,
};
