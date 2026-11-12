---
name: test-sweet
description: Plan only the necessary tests for each build step of a plan, spec, or PRD, then write a step's tests first when you build it.
disable-model-invocation: true
---

# Test Sweet

Every test carries a **warrant**: the promise or the risk that makes it necessary. A candidate with no warrant is **cut**, and the cut is recorded with its reason.

- **Promise**: a behaviour the source says the step delivers, visible from outside the code to a user, a caller, or another system.
- **Risk**: a way the step could fail that is on the risk list: lost or corrupted data, money, security and login, privacy, an action that cannot be undone, or whatever the user named as worst-if-broke.

Two branches:

- `/test-sweet <source>` plans the tests. Follow the steps below.
- `/test-sweet step <id>` builds one step test-first. Follow [build-step.md](build-step.md).

## Plan

### 1. Read the source

The source is one of:

- **A file**: read it whole.
- **GitHub issues**: a number, a URL, or several. Read each with `gh issue view <n> --json number,title,body,comments`.
- **A tickets folder**: read every ticket file in it.
- **Pasted text**: save it to `test-sweet/<slug>.source.md` first, so the plan has a source to re-read later.

Done when you hold the full text of every part of the source.

### 2. Find the build steps

A step is a unit of build work the source puts in order: a phase, milestone, task, ticket, or issue. Order tickets and issues by their blocking edges.

When the source describes features with no build order, stop. Tell the user the source has no build steps, and that a planning skill such as `/to-tickets`, `/to-issues`, or `/plan-feature` turns it into one.

Done when every step has an id, a name, and a place in the order, or you have stopped.

### 3. Settle the stack

Read the project's manifest and its existing tests for the language, the test runner, the command that runs the suite, and what the existing tests already cover. A project with no code yet takes its language from the source.

When there is no test runner, ask the user to choose one. Offer the most widely used runner for that language as the recommendation and say in one plain sentence what a test runner is.

Done when you can state the language, the runner, and the run command.

### 4. Ask the worst-if-broke question

Ask once per plan: "If one thing in this app broke, what would hurt most?" The answer joins the risk list for this plan. On a re-run, reuse the answer saved in the plan.

### 5. Apply the warrant rule to every step

For each step, list the candidates: one per promise the step makes, and one per risk-list failure the step introduces. Then rule on each:

- **Keep** it with its warrant. A promise warrant quotes the source line. A risk warrant names the risk-list entry.
- **By hand**: a warranted candidate that only a person or a real outside service can check, such as a manual checklist run or a one-off action by the owner. Record what to check and when.
- **Cut** it with a reason.

Place each kept test in the earliest step where its behaviour first exists. One warrant gets one test. When the source lists cases for a warrant, that test is a table of those cases.

These candidates are cut:

- behaviour that belongs to a framework or library
- mistakes the compiler or type checker already rejects
- internal structure that is invisible from outside the code
- a second test for a warrant that already has one
- behaviour an existing test already covers, naming that test
- behaviour that a later step delivers
- colour, spacing, and styling (text that carries information is behaviour)
- documentation

A step whose candidates are all cut is recorded as "no tests needed" with the reason.

Done when every promise in every step is a kept test, a by-hand check, or a recorded cut.

### 6. Pick each test's level

Give each kept test the cheapest level that would go red on the bug, with a clause saying why:

1. **Unit**: one piece of code on its own. Fastest.
2. **Integration**: pieces working together, with the real database or files.
3. **End-to-end**: the running app, driven the way a user drives it. Slowest.

### 7. Write the plan

Write `test-sweet/<slug>.md` in the layout from [plan-format.md](plan-format.md). The slug comes from the source: the file name, the tickets folder name, `issue-<n>` for one issue or for several that share parent `<n>`, or a short title for unrelated issues and pasted text.

A re-run on the same source updates that file. Tests whose warrant is unchanged keep their status.

### 8. Get approval

The user decides what gets tested and may be new to testing. Present the plan in chat step by step, in plain words: how many tests are kept at each level, each test kept for a risk, each by-hand check, each cut with its reason, and each ruling you were unsure of. Give the totals and the plan's path, where every kept test is listed. Define a testing term the first time it appears.

Apply the changes the user asks for. A test the user asks for is kept with the warrant "user request".

Done when the user has approved and the plan file carries `Approved: <date>`. Then tell them `/test-sweet step <first id>` starts the build.
