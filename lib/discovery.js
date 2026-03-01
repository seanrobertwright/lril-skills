'use strict';

const fs = require('fs');
const path = require('path');

/**
 * Parse YAML front matter from a SKILL.md file.
 * Handles the subset of YAML needed: simple key-value pairs, multi-line strings, arrays.
 */
function parseFrontMatter(content) {
  const match = content.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!match) return null;

  const yaml = match[1];
  const meta = {};
  let currentKey = null;
  let currentValue = '';
  let inMultiline = false;

  for (const line of yaml.split(/\r?\n/)) {
    // Key-value pair at root level
    const kvMatch = line.match(/^(\w[\w-]*):\s*(.*)/);
    if (kvMatch && !inMultiline) {
      // Save previous key if multiline
      if (currentKey) {
        meta[currentKey] = currentValue.trim();
      }

      currentKey = kvMatch[1];
      const val = kvMatch[2].trim();

      // Check for block scalar (>)
      if (val === '>' || val === '|') {
        inMultiline = true;
        currentValue = '';
        continue;
      }

      // Array item inline not supported at root, just save as string
      currentValue = val;
      meta[currentKey] = val;
      currentKey = null;
      continue;
    }

    // Array items (  - value)
    if (line.match(/^\s+-\s+/)) {
      const itemVal = line.replace(/^\s+-\s+/, '').trim();
      if (currentKey) {
        if (!Array.isArray(meta[currentKey])) {
          meta[currentKey] = [];
        }
        meta[currentKey].push(itemVal);
      }
      continue;
    }

    // Continuation of multiline
    if (inMultiline && currentKey) {
      if (line.match(/^\s/) || line === '') {
        currentValue += ' ' + line.trim();
      } else {
        // End of multiline
        meta[currentKey] = currentValue.trim();
        inMultiline = false;
        // Re-process this line
        const kv2 = line.match(/^(\w[\w-]*):\s*(.*)/);
        if (kv2) {
          currentKey = kv2[1];
          currentValue = kv2[2].trim();
          meta[currentKey] = currentValue;
          currentKey = null;
        }
      }
    }
  }

  // Flush last key
  if (currentKey && inMultiline) {
    meta[currentKey] = currentValue.trim();
  }

  return meta;
}

/**
 * Discover all skills in the skills/ directory.
 * Each skill must have a SKILL.md with YAML front matter containing at least a 'name'.
 * @param {string} skillsDir - Path to the skills/ directory
 * @returns {Array<{name: string, description: string, dir: string, meta: object}>}
 */
function discoverSkills(skillsDir) {
  if (!fs.existsSync(skillsDir)) return [];

  const skills = [];
  const entries = fs.readdirSync(skillsDir, { withFileTypes: true });

  for (const entry of entries) {
    if (!entry.isDirectory()) continue;

    const skillDir = path.join(skillsDir, entry.name);
    const skillMd = path.join(skillDir, 'SKILL.md');

    if (!fs.existsSync(skillMd)) continue;

    const content = fs.readFileSync(skillMd, 'utf-8');
    const meta = parseFrontMatter(content);

    if (!meta || !meta.name) continue;

    // Truncate description for display
    let desc = meta.description || '';
    if (desc.length > 100) {
      desc = desc.substring(0, 97) + '...';
    }

    skills.push({
      name: meta.name,
      description: desc,
      dir: skillDir,
      dirName: entry.name,
      meta,
    });
  }

  return skills.sort((a, b) => a.name.localeCompare(b.name));
}

module.exports = { discoverSkills, parseFrontMatter };
