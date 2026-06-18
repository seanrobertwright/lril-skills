---
description: Execute an implementation plan
argument-hint: [path-to-plan]
---

# Execute: Implement from Plan

## Plan to Execute

Read plan file: `$ARGUMENTS`

## Execution Instructions

### 1. Read and Understand

- Read the ENTIRE plan carefully
- Understand all tasks and their dependencies
- Note the validation commands to run
- Review the testing strategy

### 2. Execute Tasks in Order

For EACH task in "Step by Step Tasks":

#### a. Navigate to the task
- Identify the file and action required
- Read existing related files if modifying

#### b. Implement the task
- Follow the detailed specifications exactly
- Maintain consistency with existing code patterns
- Include proper type hints and documentation
- Add structured logging where appropriate

#### c. Verify as you go
- After each file change, check syntax
- Ensure imports are correct
- Verify types are properly defined

### 3. Implement Testing Strategy

After completing implementation tasks:

- Create all test files specified in the plan
- Implement all test cases mentioned
- Follow the testing approach outlined
- Ensure tests cover edge cases

### 4. Run Validation Commands (these are GATES, not a checklist)

Execute ALL validation commands from the plan in order. Treat each as a blocking gate:

- **Run it, paste the actual output, and report the exit code.** Do not mark a level "passed"
  without showing evidence. A level is green only when its command exits 0.
- **Level 1 must be the repo-root typecheck/build** (e.g. `npm run typecheck` / root `tsc -b`),
  not a per-workspace build — only the root build covers cross-project and test-only imports.
  (A broken root typecheck once shipped through two milestones because only per-workspace builds
  were run.)

If any command fails:
- Fix the issue
- Re-run the command
- Continue only when it passes (exit 0)

- **Confirm the integration layer actually RAN, not just that the suite was green.** Many test
  setups make DB/infra-backed tests self-skip when an env var is unset (e.g.
  `describe.skipIf(!process.env.DATABASE_URL_TEST)`), and a skipped layer still reports PASS —
  `skipped ≠ passed`. If the repo has integration tests (e.g. `*.int.test.ts`), bring the
  infra up and re-run so they execute. vitest prints a skipped count; a "passed" suite with the
  integration files skipped means that layer was never exercised. If the project provides a
  stricter mode (e.g. `repo-health --require-db` that fails on skipped int tests), use it for
  sign-off. (A latent type bug once shipped because an int test never ran against a real DB.)

### 4.5 Pre-commit hygiene gate

Before handing off to commit, confirm the working tree is clean of artifacts and corruption.
If the project defines a single health gate (e.g. `npm run repo-health`), run that. Otherwise run
these directly:

- **Binary/corruption check:** `git diff --cached --numstat | grep -P '^-\t-\t'` flags files git
  treats as binary. New source files must be valid UTF-8 — green typecheck + tests do NOT prove a
  file is clean text (compilers tolerate NUL bytes in comments).
- **Stray-artifact check:** `git status --porcelain` shows no emitted `*.js`/`*.d.ts`/`*.map` under
  any `src/`, and no `dist/` or `*.sqlite`/`*.db` staged.
- **Resource-teardown check (new long-lived resources):** for any `setInterval`/`setTimeout`, stream
  (SSE), event listener, subscription, or proxied upstream `fetch` you added, confirm a teardown path
  on disconnect/abort AND that it is armed BEFORE the first `await` (a disconnect during the initial
  await fires `close`/abort before a later-attached listener exists → leaked timer/stream). Pass
  `request.signal` to a proxy `fetch` so the upstream cancels with the client. `tsc`+tests do NOT catch
  these leak windows — run `/lril:code-review` before commit (it caught exactly this class in M9: an SSE
  interval leak, a missing proxy abort signal, and a NaN-timestamp fall-through).

### 5. Final Verification

Before completing:

- ✅ All tasks from plan completed
- ✅ All tests created and passing
- ✅ All validation commands pass
- ✅ Code follows project conventions
- ✅ Documentation added/updated as needed

## Output Report

Provide summary:

### Completed Tasks
- List of all tasks completed
- Files created (with paths)
- Files modified (with paths)

### Tests Added
- Test files created
- Test cases implemented
- Test results

### Validation Results
```bash
# Output from each validation command
```

### Ready for Commit
- Confirm all changes are complete
- Confirm all validations pass
- Ready for `/lril:commit` command

## Notes

- If you encounter issues not addressed in the plan, document them
- If you need to deviate from the plan, explain why
- If tests fail, fix implementation until they pass
- Don't skip validation steps
