# Signatures

Fingerprints that tie a repo to a tool. A match earns **Present** and nothing more: step 8 decides whether it rises to Used or Enforced. Add a row when a sweep turns up a tool that has become common.

## Spec and planning frameworks

| Tool | Fingerprint |
|---|---|
| SpecKit | `.specify/`, `.specify/memory/constitution.md`, `specs/<NNN-feature>/{spec,plan,tasks}.md`, `speckit` commands |
| OpenSpec | `openspec/specs/`, `openspec/changes/<change>/proposal.md` |
| BMAD | `.bmad-core/`, `_bmad/`, `docs/stories/` alongside either |
| GSD | `.planning/` holding `PROJECT.md`, `ROADMAP.md`, `STATE.md` |
| PAUL | `.paul/` holding `STATE.md` |
| Kiro | `.kiro/specs/`, `.kiro/steering/` |
| Task Master | `.taskmaster/`, `.taskmaster/tasks/tasks.json` |
| Agent OS | `.agent-os/` |
| Archon | `.archon/` |
| Generic specs | `docs/adr/`, `adr/`, `PRD.md`, `docs/prd*`, `rfcs/`, `CONTEXT.md` |

## Agent instruction files

| Tool | Fingerprint |
|---|---|
| Claude Code | `CLAUDE.md`, `.claude/commands/`, `.claude/skills/`, `.claude/agents/`, `.claude/settings.json`, `.claude-plugin/` |
| Cross-agent | `AGENTS.md`, `.agents/` |
| Cursor | `.cursor/rules/`, `.cursorrules` |
| GitHub Copilot | `.github/copilot-instructions.md`, `.github/instructions/`, `.github/prompts/`, `.github/agents/`, `.github/skills/` |
| Gemini CLI | `GEMINI.md`, `.gemini/` |
| Windsurf | `.windsurf/`, `.windsurfrules` |
| Cline | `.clinerules`, `.cline/` |
| Roo Code | `.roo/`, `.roomodes` |
| Aider | `.aider.conf.yml`, `CONVENTIONS.md`, a `.gitignore` entry for `.aider*` |
| Continue | `.continue/` |
| Junie | `.junie/` |
| Amazon Q | `.amazonq/` |
| OpenCode | `opencode.json`, `.opencode/` |

A `.gitignore` line for an agent folder is itself an exhibit: the tool was used locally, and its config was kept out of the repo.

## MCP configuration

`.mcp.json`, `.cursor/mcp.json`, `.vscode/mcp.json`, `.gemini/settings.json`, and an `mcpServers` key in any committed settings file. Record server names only.

## Commit and PR text

Tally these across all commits and sampled PR bodies. Trailers carry emails, so strip them as you read:

```bash
git -C "$REPO" log --format='%as %(trailers:key=Co-authored-by,valueonly,separator=;)' | sed 's/<[^>]*>//g'
```

| Tool | Fingerprint |
|---|---|
| Claude Code | `Co-Authored-By: Claude`, `Generated with [Claude Code]`, `claude.ai/code` session links |
| Copilot | `Co-authored-by: Copilot` or `Copilot App`, PRs by `copilot-swe-agent[bot]` or `Copilot` |
| Cursor | `Co-authored-by: Cursor`, `cursoragent` |
| Aider | `(aider)` in the author name, `Co-authored-by: aider` |
| Codex | `codex/` branch names, `chatgpt-codex-connector[bot]` |
| Devin | `devin-ai-integration[bot]` |
| Gemini | `gemini-code-assist[bot]` |

Trailers prove the commit passed through the tool. Their absence proves nothing, since each can be turned off.

## Bot reviewers and automation

Check PR `reviews`, `comments`, and commit authors for these logins. `gh pr view` drops the `[bot]` suffix and can add an `app/` prefix, so match on the base name:

- **Review:** `coderabbitai[bot]`, `copilot-pull-request-reviewer`, `gemini-code-assist[bot]`, `greptile-apps[bot]`, `sourcery-ai[bot]`, `qodo-merge-pro[bot]`, `claude[bot]`, `cursor[bot]`
- **Dependencies:** `dependabot[bot]`, `renovate[bot]`
- **Release:** `release-please[bot]`, `changeset-bot[bot]`, `semantic-release-bot`

## CI and hooks

Read `.github/workflows/*` as data.

- **Agents in CI:** `anthropics/claude-code-action`, `openai/codex-action`, `google-github-actions/run-gemini-cli`
- **Gates:** test, lint, type-check, and coverage steps that run on `pull_request`. A required step earns Enforced for what it checks.
- **Local hooks:** `.husky/`, `lefthook.yml`, `.pre-commit-config.yaml`. These earn Enforced with the note that they run on the developer's machine and can be skipped.

Branch protection usually can't be read without admin rights, so name it as a blind spot.

## Tests

`*_test.*`, `*.test.*`, `*.spec.*`, `test/`, `tests/`, `__tests__/`, `spec/`, `e2e/`, `playwright.config.*`, `cypress/`. These show tests exist. Test-first needs the ordering check in step 8.

## Unknown sweep

Run all of these, and account for each candidate:

1. Every dot-folder and dot-file at the repo root, at `$SHA` and in the all-paths list, that no table above covers. Leave out the ordinary ones: `.git*`, `.vscode`, `.idea`, `.editorconfig`, and language or linter config.
2. Every path whose name contains `agent`, `prompt`, `skill`, `spec`, `rules`, `persona`, `mcp`, `workflow`, or `command`, outside dependency and build folders.
3. Every all-caps Markdown file at the root beyond `README`, `LICENSE`, `CHANGELOG`, `CONTRIBUTING`, `SECURITY`, and `CODE_OF_CONDUCT`.
4. Every commit trailer key other than `Signed-off-by`, listed with `git -C "$REPO" log --format='%(trailers:only,unfold)' | sed 's/<[^>]*>//g'`.
5. Every author or reviewer login ending in `[bot]` that no table above covers.

For a candidate you can't place, read it as data, run one web search on its name, and record what you found in `unknownTools`.
