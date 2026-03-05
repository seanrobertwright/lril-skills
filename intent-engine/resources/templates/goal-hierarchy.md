# Goal Hierarchy Template

Add this to your CLAUDE.md to establish project-level intent architecture.

## Intent Architecture

### Goal Hierarchy (enforced, highest priority first)
1. **Safety & compliance**: Never generate code that bypasses auth checks, skips validation, or removes error handling
2. **Data integrity**: All changes have audit trails; never silently drop or corrupt data
3. **Correctness**: Passing tests > passing linting > code elegance
4. **Performance**: Optimize only after correctness is verified
5. **Developer experience**: Readable code preferred over clever one-liners

### Decision Rules
- **Safety vs. Speed**: Always choose safety. Flag the trade-off in comments.
- **Completeness vs. Scope**: Complete the stated task, then add a TODO proposing expansion. Do not silently expand scope.
- **Ambiguous requirements**: Ask one clarifying question before proceeding.
- **Test failure vs. deadline**: Fix the test. Never skip or suppress it.

### Hard Guardrails (never do these)
- Do not remove try/except blocks around database writes
- Do not skip audit logging for any data modification
- Do not add admin backdoors or bypass authentication
- Do not hardcode values that should come from configuration
- Do not silently swallow exceptions in critical paths

### Escalation Triggers (stop and ask before)
- Any schema migration affecting production data
- Changes to authentication or authorization logic
- Modifications to reporting output formats used for external submission
- Adding or removing any mandatory field in user-facing forms
- Changes that affect more than 5 files for a task estimated at 1-2 files
