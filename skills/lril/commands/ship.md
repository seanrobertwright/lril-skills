---
description: Ship the current branch — sync with base, validate, review the diff, bump the version, update the changelog, commit, push, and open the PR
---

Take the work on this branch from "I think it's done" to "there is a PR waiting for review",
stopping at the first thing that is not ready rather than pushing through it.

Never skip a phase because it looks fine. Report what each phase found before moving on.

## Phase 1 — Preflight

```bash
git rev-parse --is-inside-work-tree
git branch --show-current
git status --porcelain
git log --oneline @{u}..HEAD 2>/dev/null || git log --oneline -10
```

Stop and ask the user how to proceed if any of these are true:

- **You are on the base branch** (`main`, `master`, `dev`). Offer to create a branch from the current
  commit and move the work onto it. Never ship straight from the base branch.
- **A rebase, merge, or cherry-pick is in progress.** Finish it first.
- **There are uncommitted changes.** Show them and ask: include them in this ship, or stash them.
- **There is nothing to ship** — no commits ahead of the base and nothing uncommitted. Say so and stop.

## Phase 2 — Sync with the base branch

Detect the base rather than assuming it:

```bash
git remote show origin 2>/dev/null | sed -n 's/.*HEAD branch: //p'
```

Fall back to whichever of `main`, `master`, `dev` exists. If the branch was cut from something else
(a release branch, a stacked feature branch), ask before assuming.

```bash
git fetch origin --prune
git merge --no-edit origin/<base>
```

If the merge conflicts, stop. Resolve them properly — the `resolving-merge-conflicts` skill covers the
process — then re-run this phase. Do not `git checkout --ours/--theirs` your way out of it.

## Phase 3 — Validate

Detect the toolchain from the repo instead of guessing: `package.json` scripts, `Makefile`,
`pyproject.toml`, `Cargo.toml`, `go.mod`, CI workflow files. If the project has a documented
validation routine, use it — `/lril:validate` if this repo is set up for it.

Run, in this order, whichever exist: **tests → type check → lint → build**.

- Any failure stops the ship. Report the failing output verbatim.
- Do not "fix" a failure by weakening a test, skipping it, or loosening a lint rule.
- If the user explicitly says to ship anyway, say clearly in the PR body that validation failed and
  what failed.

## Phase 4 — Review the diff

```bash
git diff origin/<base>...HEAD --stat
git diff origin/<base>...HEAD
```

Read the whole diff before writing anything about it. Look for: debug statements and stray
`console.log`, commented-out code, secrets or tokens, `.env` files, large binaries, TODOs added in
this branch, and anything in the diff the branch was not supposed to touch.

Run `/lril:code-review` for a full pre-commit review when the diff is more than a trivial change.
Fix what it finds, or record it as a known limitation in the PR body — never silently ignore it.

## Phase 5 — Version and changelog

Find the version where this project actually keeps it: a `VERSION` file, `package.json`,
`pyproject.toml`, `Cargo.toml`, `__init__.py`, or a git tag. If the project does not version, skip to
Phase 6 and say so.

Choose the bump from the commits in this branch:

| Commits contain | Bump |
|---|---|
| a breaking change (`!` or `BREAKING CHANGE:`) | major |
| any `feat:` | minor |
| only `fix:`, `docs:`, `chore:`, `refactor:`, `test:` | patch |

Show the user the proposed version and let them override it. When the
change is ambiguous (a `feat` that is really a bug fix, a refactor with a behaviour change), ask
rather than deciding silently.

Update the changelog if the project has one, in the style already used in the file (usually
[Keep a Changelog](https://keepachangelog.com)): a new section for the version and today's date,
entries grouped under Added / Changed / Fixed / Removed, written for someone using the project rather
than for someone reading the diff. One line per user-visible change; internal refactors do not need
an entry.

## Phase 6 — Commit and push

Commit the version bump and changelog together with a conventional message:

```bash
git add -A
git commit -m "chore(release): v<version>"
git push -u origin <branch>
```

Never `--force` and never `--no-verify`. If a hook fails, fix the cause — that is what the hook is
for. If the push is rejected because the remote moved, fetch and re-run Phase 2.

## Phase 7 — Open the pull request

```bash
gh pr create --base <base> --head <branch> --title "<title>" --body-file -
```

- **Title:** conventional prefix plus what actually changed, in plain words. Not the branch name.
- **Body:** what changed and why, how it was verified (name the tests you ran), anything a reviewer
  should look at closely, and any known limitation. Link the issue if the branch references one.
- **Confirm the title and body with the user before creating the PR.** It is public, it is on their
  account, and it is the first thing a reviewer reads.

If `gh` is missing or unauthenticated, or there is no remote, stop after Phase 6 and give the user the
compare URL to open it themselves. Do not treat that as a failure of the ship — the work is pushed.

Report at the end: base branch, version shipped, what validation ran and passed, the PR URL, and
anything you flagged but did not fix.
