# Plan format

`test-sweet/<slug>.md` uses this layout.

```markdown
# Test plan: <source title>

- Source: <file path, tickets folder, issue numbers, or test-sweet/<slug>.source.md>
- Language: <language>
- Test runner: <runner>
- Run command: `<command that runs the whole suite>`
- Worst if broke: <the user's answer>
- Approved: <YYYY-MM-DD, added when the user approves>

## Step <id>: <name>

| ID | Behaviour tested | Warrant | Level | Why this level | Status |
|---|---|---|---|---|---|
| <step id>.1 | <what the app does, in plain words> | Promise: "<source line>" | Unit | <clause> | planned |
| <step id>.2 | <what must keep holding> | Risk: <risk-list entry> | Integration | <clause> | planned |

By hand:

- <what a person checks, and when>

Cut:

- <candidate>: <reason>

## Step <id>: <name>

No tests needed: <reason>
```

Rules for the fields:

- **ID** is the step id, a dot, and a number. An ID stays with its test across re-runs.
- **Warrant** starts with `Promise:`, `Risk:`, or `User request`.
- **Status** is `planned`, `red`, or `green`.
- **By hand** and **Cut** are left out of a step that has none.
- Every step in the source has a section, in build order.
