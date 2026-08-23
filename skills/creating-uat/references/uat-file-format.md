# UAT markdown file format (v1)

This is the contract between the four scripts. The markdown file is the source of truth; the HTML
form is generated from it and the completed answers are written back into it.

**Never hand-edit the HTML.** Edit the `.md`, then re-run the generator.

---

## 1. Marker syntax

All machine-readable structure lives in HTML comments so the markdown still renders cleanly on
GitHub and in any editor.

| Marker | Where | Purpose |
|---|---|---|
| `<!-- uat:meta ... -->` | once, after the H1 | key/value run metadata |
| `<!-- uat:summary:start -->` … `<!-- uat:summary:end -->` | once, after meta | rewritten on submit with run results |
| `<!-- uat:section id=N title="..." -->` | after each `## ` section heading | starts a section |
| `<!-- uat:test id=N.M -->` | after each `### ` test heading | starts a test |
| `<!-- uat:answer:start id=N.M -->` … `<!-- uat:answer:end id=N.M -->` | end of each test | the tester's answer; rewritten on submit |
| `<!-- uat:findings:start -->` … `<!-- uat:findings:end -->` | once, near the end | ad-hoc tester-reported findings; rewritten on submit |

Rules:

- `id` values are unique within the file. Tests use `N.M` (dotted section.item). Sections use `N`.
- IDs must match `[A-Za-z0-9._-]+`. They become filenames for screenshots, so nothing else is legal.
- A `##` heading **without** a `uat:section` marker is prose (e.g. "How to use this checklist",
  "Glossary", "Not in scope"). The generator shows it as intro/appendix text and never turns it
  into tests. Put deferred/out-of-scope notes there.
- Everything between `<!-- uat:test id=X -->` and `<!-- uat:answer:start id=X -->` is the test body
  and is rendered read-only in the HTML.

## 2. Canonical skeleton

```markdown
# MyApp — User Acceptance Test

<!-- uat:meta
version: 1
app: MyApp
generated: 2026-08-23
commit: a1b2c3d
branch: main
repo: E:/Projects/MyApp
-->

<!-- uat:summary:start -->
_This UAT has not been run yet._
<!-- uat:summary:end -->

## How to use this checklist

Plain-language instructions for the tester. Rendered at the top of the HTML form.

## Glossary

- **Terminal** — the black window where you type commands...

## Section 1 — Setting up
<!-- uat:section id=1 title="Setting up" -->

### 1.1  Check that Docker is installed
<!-- uat:test id=1.1 -->

- **Goal (plain words):** Make sure the program that runs the app's database is on your computer.
- **Before you start:** Nothing. This is the first test.
- **Steps:**
  1. Open a terminal (Section 0 shows you how).
  2. Type exactly this and press Enter: `docker --version`
  3. Wait about two seconds.
- **PASS looks like:** A line appears starting with `Docker version` followed by numbers.
- **If it does not work:** Write down the exact red text you see.

<!-- uat:answer:start id=1.1 -->
- [ ] **Status:** _not answered_
- **Notes:**
- **Look & feel concern:**
- **Screenshots:**
<!-- uat:answer:end id=1.1 -->

## Not in scope (deferred — do NOT test)

- Email delivery — not built yet.

<!-- uat:findings:start -->
_No tester-reported findings yet._
<!-- uat:findings:end -->

## Sign-off

- Tester name: ______  Date: ______
```

## 3. Answer block, before and after

Empty (what the author writes, or what the generator injects automatically):

```markdown
<!-- uat:answer:start id=3.2 -->
- [ ] **Status:** _not answered_
- **Notes:**
- **Look & feel concern:**
- **Screenshots:**
<!-- uat:answer:end id=3.2 -->
```

Filled by the server on submit:

```markdown
<!-- uat:answer:start id=3.2 -->
- [!] **Status:** FAIL
- **Notes:** I clicked the blue Save button and nothing happened. No message appeared.
- **Look & feel concern:** (Annoying) The text in the form is too small to read on my laptop.
- **Screenshots:**
  - ![3.2 screenshot 1](assets/UAT-myapp-2026-08-23/3.2-1.png)
<!-- uat:answer:end id=3.2 -->
```

Status line encoding — the checkbox keeps the file readable as a checklist:

| Status | Line |
|---|---|
| Pass | `- [x] **Status:** PASS` |
| Pass with a concern attached | `- [x] **Status:** PASS` (concern on its own line) |
| Fail | `- [!] **Status:** FAIL` |
| Not done | `- [~] **Status:** NOT DONE` |
| Unanswered | `- [ ] **Status:** _not answered_` |

Severity words for concerns: `Cosmetic`, `Annoying`, `Blocks me`. Rendered as `(Severity) text`.

## 4. Summary block, rewritten on submit

```markdown
<!-- uat:summary:start -->
> **Run status:** COMPLETE — submitted 2026-08-23 15:04 by Sean
> **Result:** 41 of 47 passed · 4 failed · 2 not done · 6 look-and-feel concerns · 3 findings
>
> | Status | Count |
> |---|---|
> | Pass | 41 |
> | Fail | 4 |
> | Not done | 2 |
> | Unanswered | 0 |
>
> **Failed tests:** 2.4, 3.2, 5.1, 6.3
> **Tests with concerns:** 1.2, 3.2, 3.5, 4.1, 4.2, 7.1
<!-- uat:summary:end -->
```

A partial submit writes `**Run status:** PARTIAL` and lists the unanswered IDs.

## 5. Findings block, rewritten on submit

```markdown
<!-- uat:findings:start -->
### F1 — Sidebar disappears when the window is narrow
- **Reported from:** Section 3 (Dashboard)
- **Severity:** Annoying
- **What happened:** When I made the window smaller the menu on the left vanished and I could not
  find a way to get it back.
- **Screenshots:**
  - ![F1 screenshot 1](assets/UAT-myapp-2026-08-23/F1-1.png)
<!-- uat:findings:end -->
```

## 6. Sidecar files

Written next to the markdown, in the same directory:

| File | Written by | Purpose |
|---|---|---|
| `<name>.html` | generator | the form the tester fills in |
| `.uat-progress-<slug>.json` | server, on Save | in-progress answers so work is never lost |
| `<name>.results.json` | server, on Submit | machine-readable results for tooling |
| `assets/<slug>/<id>-<n>.<ext>` | server, on screenshot upload | screenshots, referenced relatively from the md |

`<slug>` is the markdown filename without its `.md` extension.

`results.json` shape:

```json
{
  "uat": "UAT-myapp-2026-08-23.md",
  "tester": "Sean",
  "submitted": "2026-08-23T15:04:11",
  "partial": false,
  "counts": {"pass": 41, "fail": 4, "notdone": 2, "unanswered": 0, "concerns": 6, "findings": 3},
  "answers": {
    "3.2": {
      "status": "fail",
      "title": "Save a new report",
      "section": "3",
      "notes": "...",
      "concern": "...",
      "severity": "annoying",
      "screenshots": ["assets/UAT-myapp-2026-08-23/3.2-1.png"]
    }
  },
  "findings": [
    {"id": "F1", "section": "3", "title": "...", "description": "...", "severity": "annoying",
     "screenshots": ["assets/UAT-myapp-2026-08-23/F1-1.png"]}
  ]
}
```

## 7. Submit validation

**Full submit** is refused unless all of the following hold. The server enforces these; the browser
mirrors them so the tester sees problems before clicking.

1. Every test has a status of `pass`, `fail` or `notdone`.
2. Every `fail` has a non-empty **Notes** of at least 10 characters.
3. Every `notdone` has a non-empty **Notes** explaining why it could not be done.
4. Every non-empty **Look & feel concern** has a severity selected.
5. Every ad-hoc finding has a title and a description.
6. A tester name is filled in.

**Partial submit** skips rules 1–3 for unanswered tests only; rules 2–6 still apply to anything the
tester did fill in. The markdown and `results.json` are marked `PARTIAL` and unanswered IDs are
listed in the summary block so nobody mistakes it for a clean run.

## 8. Generator normalisation

Running the generator is idempotent and self-healing. It rewrites the `.md` in place to:

- inject an empty answer block for any `uat:test` that lacks one,
- inject the `uat:summary` block if absent,
- inject the `uat:findings` block if absent,
- leave every existing answer, including filled-in ones, untouched.

It refuses to run and reports the problem when it finds duplicate IDs, a test outside any section,
an answer block whose `id` does not match its test, or an ID with illegal characters.
