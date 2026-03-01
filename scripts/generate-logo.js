#!/usr/bin/env node
'use strict';

// Generates an SVG logo from the ASCII art by rendering each character
// as colored SVG rectangles — no font dependency, pixel-perfect alignment.

const fs = require('fs');
const path = require('path');

const LINES = [
  '██╗     ██████╗  ██╗██╗           ███████╗██╗  ██╗██╗██╗     ██╗     ███████╗',
  '██║     ██╔══██╗ ██║██║           ██╔════╝██║ ██╔╝██║██║     ██║     ██╔════╝',
  '██║     ██████╔╝ ██║██║     █████╗███████╗█████╔╝ ██║██║     ██║     ███████╗',
  '██║     ██╔══██╗ ██║██║     ╚════╝╚════██║██╔═██╗ ██║██║     ██║     ╚════██║',
  '███████╗██║  ██║ ██║███████╗      ███████║██║  ██╗██║███████╗███████╗███████║',
  '╚══════╝╚═╝  ╚═╝ ╚═╝╚══════╝      ╚══════╝╚═╝  ╚═╝╚═╝╚══════╝╚══════╝╚══════╝',
];

// Characters that should be rendered as filled blocks
const FILL_CHARS = new Set(['█', '╗', '╔', '═', '║', '╝', '╚']);

const GRADIENT = [
  [0, 200, 255],   // cyan
  [40, 170, 255],  // light blue
  [80, 140, 255],  // blue
  [120, 120, 255], // blue-purple
  [160, 100, 255], // purple
  [200, 80, 240],  // magenta
  [240, 70, 200],  // pink
];

function interpolateColor(t) {
  const segLen = GRADIENT.length - 1;
  const seg = Math.min(Math.floor(t * segLen), segLen - 1);
  const segT = (t * segLen) - seg;
  const c1 = GRADIENT[seg];
  const c2 = GRADIENT[seg + 1] || c1;
  const r = Math.round(c1[0] + (c2[0] - c1[0]) * segT);
  const g = Math.round(c1[1] + (c2[1] - c1[1]) * segT);
  const b = Math.round(c1[2] + (c2[2] - c1[2]) * segT);
  return `rgb(${r},${g},${b})`;
}

const CELL_W = 9;
const CELL_H = 16;
const PAD = 4;

// Find max line length
const maxLen = Math.max(...LINES.map(l => [...l].length));
const svgW = maxLen * CELL_W + PAD * 2;
const svgH = LINES.length * CELL_H + PAD * 2;

let rects = '';

for (let row = 0; row < LINES.length; row++) {
  const chars = [...LINES[row]]; // spread to handle multi-byte chars properly
  for (let col = 0; col < chars.length; col++) {
    const ch = chars[col];
    if (ch === ' ') continue;

    const t = maxLen > 1 ? col / (maxLen - 1) : 0;
    const color = interpolateColor(t);
    const x = PAD + col * CELL_W;
    const y = PAD + row * CELL_H;

    if (ch === '█') {
      rects += `  <rect x="${x}" y="${y}" width="${CELL_W}" height="${CELL_H}" fill="${color}"/>\n`;
    } else if (ch === '║') {
      // vertical bar — two thin columns on left and right
      const bw = 3;
      rects += `  <rect x="${x}" y="${y}" width="${bw}" height="${CELL_H}" fill="${color}"/>\n`;
      rects += `  <rect x="${x + CELL_W - bw}" y="${y}" width="${bw}" height="${CELL_H}" fill="${color}"/>\n`;
    } else if (ch === '═') {
      // horizontal double line — two thin rows top and bottom
      const bh = 3;
      rects += `  <rect x="${x}" y="${y + 2}" width="${CELL_W}" height="${bh}" fill="${color}"/>\n`;
      rects += `  <rect x="${x}" y="${y + CELL_H - bh - 2}" width="${CELL_W}" height="${bh}" fill="${color}"/>\n`;
    } else if (ch === '╗') {
      // top-right corner
      const bw = 3;
      const bh = 3;
      rects += `  <rect x="${x}" y="${y + 2}" width="${CELL_W}" height="${bh}" fill="${color}"/>\n`;
      rects += `  <rect x="${x}" y="${y + CELL_H - bh - 2}" width="${CELL_W - bw}" height="${bh}" fill="${color}"/>\n`;
      rects += `  <rect x="${x}" y="${y}" width="${bw}" height="${CELL_H}" fill="${color}"/>\n`;
      rects += `  <rect x="${x + CELL_W - bw}" y="${y + 2}" width="${bw}" height="${CELL_H - 2}" fill="${color}"/>\n`;
    } else if (ch === '╔') {
      // top-left corner
      const bw = 3;
      const bh = 3;
      rects += `  <rect x="${x}" y="${y + 2}" width="${CELL_W}" height="${bh}" fill="${color}"/>\n`;
      rects += `  <rect x="${x + bw}" y="${y + CELL_H - bh - 2}" width="${CELL_W - bw}" height="${bh}" fill="${color}"/>\n`;
      rects += `  <rect x="${x}" y="${y + 2}" width="${bw}" height="${CELL_H - 2}" fill="${color}"/>\n`;
      rects += `  <rect x="${x + CELL_W - bw}" y="${y}" width="${bw}" height="${CELL_H}" fill="${color}"/>\n`;
    } else if (ch === '╝') {
      // bottom-right corner
      const bw = 3;
      const bh = 3;
      rects += `  <rect x="${x}" y="${y + 2}" width="${CELL_W - bw}" height="${bh}" fill="${color}"/>\n`;
      rects += `  <rect x="${x}" y="${y + CELL_H - bh - 2}" width="${CELL_W}" height="${bh}" fill="${color}"/>\n`;
      rects += `  <rect x="${x}" y="${y}" width="${bw}" height="${CELL_H - 2}" fill="${color}"/>\n`;
      rects += `  <rect x="${x + CELL_W - bw}" y="${y}" width="${bw}" height="${CELL_H - 2}" fill="${color}"/>\n`;
    } else if (ch === '╚') {
      // bottom-left corner
      const bw = 3;
      const bh = 3;
      rects += `  <rect x="${x + bw}" y="${y + 2}" width="${CELL_W - bw}" height="${bh}" fill="${color}"/>\n`;
      rects += `  <rect x="${x}" y="${y + CELL_H - bh - 2}" width="${CELL_W}" height="${bh}" fill="${color}"/>\n`;
      rects += `  <rect x="${x}" y="${y}" width="${bw}" height="${CELL_H - 2}" fill="${color}"/>\n`;
      rects += `  <rect x="${x + CELL_W - bw}" y="${y + 2}" width="${bw}" height="${CELL_H - 2}" fill="${color}"/>\n`;
    }
  }
}

const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${svgW}" height="${svgH}" viewBox="0 0 ${svgW} ${svgH}">
${rects}</svg>
`;

const outPath = path.join(__dirname, '..', 'assets', 'logo.svg');
fs.writeFileSync(outPath, svg);
console.log(`Generated ${outPath} (${svgW}x${svgH})`);
