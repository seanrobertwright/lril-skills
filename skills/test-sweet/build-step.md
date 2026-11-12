# Build a step

`/test-sweet step <id>` builds one step of an approved plan, tests first.

## 1. Load the plan

Use the plan in `test-sweet/`. With several plans there, ask which one. A plan without an `Approved:` line goes back to step 8 of [SKILL.md](SKILL.md) first.

## 2. Re-read the step in the source

When the step's promises differ from the plan, redo steps 5 to 8 of [SKILL.md](SKILL.md) for this step before writing anything.

Done when the plan's rows for this step match the source as it stands now.

## 3. Write the tests first

A step recorded as "no tests needed" is built with no test work. Tell the user the reason and go to step 5.

Otherwise the step's kept tests are the complete list of behaviours to test, taken in plan order, each at the level the plan gives it.

- **When the `tdd` skill is available**, invoke it and hand it that list.
- **Otherwise** run this loop for each test in order:
  1. Write the one test. It exercises the behaviour through the code's public surface, so it survives a rewrite of the internals.
  2. Run it and see it **red** because the behaviour is missing. A red caused by a typo or a bad import is fixed before moving on.
  3. Write the least code that turns it **green**.
  4. Run the step's tests, then take the next test.

## 4. Rule on new candidates

A candidate that surfaces while building goes through the warrant rule in [SKILL.md](SKILL.md). A kept one is added to the plan and shown to the user before it is written.

## 5. Run the whole suite

Run every test, including those from earlier steps. They are the check that this step broke nothing.

Done when every kept test of this step and every earlier test is green. Set each test's status in the plan, and report the result as it is, naming any test that is still red. List the step's by-hand checks for the user to do.
