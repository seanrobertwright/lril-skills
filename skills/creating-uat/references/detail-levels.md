# Detail levels

The tester's skill level decides **how much detail each step carries** — never how much of the app is
covered. Coverage is the same at all three levels: every surface from Phase 1 gets a test, unhappy
paths and security checks included. What changes is how much the checklist explains, how many steps
one instruction is broken into, and what the tester is trusted to already know.

Record the chosen level in the markdown meta block so the file says who it was written for:

```
<!-- uat:meta
version: 1
app: Demo App
generated: 2026-08-23
tester_level: novice
-->
```

Ask once, in Phase 0, and apply the answer to the whole document. Do not mix levels between sections.

---

## At a glance

| | **Novice** | **Intermediate** | **Expert** |
|---|---|---|---|
| Who | has never opened a terminal; may be a stakeholder, a client, or a subject-matter expert | comfortable with a computer, can run commands, is not a developer on this project | a developer or QA engineer, possibly not on this project |
| Assumes | nothing at all | a working machine, an installed toolchain, basic terminal use | full toolchain, git, curl, reading logs, browser devtools |
| Steps | one physical action each | one logical action each | one outcome each |
| Commands | exact, complete, in full | exact, complete, in full | exact, with obvious flags left to judgement |
| Glossary | required, defines every technical word | only project-specific and domain terms | none |
| "Section 0 — before you start" | full: how to open a terminal, how to reach the folder | short prerequisite list with versions | one line of prerequisites |
| Expected result | described as what appears on screen | described as the observable outcome | stated as an assertion |
| Length | longest — a 40-test UAT can run 1,500 lines | roughly half of Novice | roughly a third of Novice |
| Diagnosis | "write down the exact red text" | "note the error and which step it came from" | "capture the failing response/log line and the relevant state" |

**The trap at every level:** never make a step's outcome a matter of opinion. If the tester could
reasonably record either Pass or Fail from the same observation, the test is written badly regardless
of level.

---

## Novice

The reader may never have used a terminal, does not know what a browser address bar is called, and
cannot fill in any blank you leave. Everything is spelled out.

Rules:

1. **One physical action per numbered step.** Opening a terminal and typing into it are two steps.
2. **Say where a thing is on screen** as well as what it is called: "the blue **Save** button at the
   bottom of the form".
3. **Never use an unexplained word.** Define it inline the first time and again in the glossary.
4. **Spell out navigation in full.** "Open your web browser, click the address bar at the very top,
   type `http://localhost:3000` and press Enter."
5. **Say how long to wait** and what "finished" looks like: "this can take two or three minutes; stop
   waiting when the typing cursor comes back".
6. **Include a Section 0** covering how to open a terminal on their operating system and how to get to
   the project folder.
7. **Branch on the unexpected**: "If you do not see X, do Y first."

### Example

```markdown
### 2.2  Sign in with the test account
<!-- uat:test id=2.2 -->

- **Goal (plain words):** Get into the app using the practice account.
- **Before you start:** Test 2.1 passed and the home page is on screen.
- **Steps:**
  1. Click the blue **Sign in** button in the top-right corner of the page.
  2. A small window appears. Click the box labelled **Email**.
  3. Type `tester@example.com`
  4. Click the box labelled **Password**.
  5. Type `demo-password-123`
  6. Click the blue **Continue** button at the bottom of the small window.
  7. Wait about two seconds.
- **PASS looks like:** The small window closes and your name, **Test User**, appears in the top-right
  corner where the Sign in button used to be.
- **If it does not work:** Write down the exact wording of any red message under the boxes, and
  attach a picture of the screen.
```

---

## Intermediate

The reader can open a terminal, run a command, and find their way around a web app, but does not know
this codebase and is not expected to reason about its internals.

Rules:

1. **One logical action per step.** "Open a terminal in the project folder and run `npm run dev`" is
   one step, not three.
2. **Still give complete commands** — never `npm run <something>`. Getting a command wrong wastes as
   much of their time as it does a novice's.
3. **Name UI elements by label**, but drop the "top-right corner, blue" scaffolding unless the element
   is genuinely hard to find.
4. **Glossary only for project vocabulary** — the domain terms and internal names this app uses. Not
   "terminal", not "browser".
5. **State prerequisites with versions**: "Docker 24+, Node 20+, a free port 3000."
6. **Expected results are observable outcomes**, not screen descriptions: "you are signed in and the
   header shows your name".

### Example

```markdown
### 2.2  Sign in with the test account
<!-- uat:test id=2.2 -->

- **Goal:** Sign in with the seeded test account.
- **Before you start:** Test 2.1 passed; the app is running on `http://localhost:3000`.
- **Steps:**
  1. Click **Sign in** and enter `tester@example.com` / `demo-password-123`.
  2. Submit the form with **Continue**.
- **PASS looks like:** You are signed in — the header shows **Test User** instead of the Sign in
  button, and reloading the page keeps you signed in.
- **If it does not work:** Note the error message shown and whether it came from the email or the
  password field.
```

---

## Expert

The reader is a developer or QA engineer. They can read a stack trace, use curl and devtools, inspect
a database, and infer the obvious. Write for speed of execution.

Rules:

1. **One outcome per step.** Bundle the mechanics; keep the assertions separate and explicit.
2. **State the assertion, not the scenery.** "Session cookie set, `HttpOnly` and `SameSite=Lax`;
   header renders the display name."
3. **Verify through whatever is fastest** — an API call, a log line, a database query — not only
   through the UI. Give the exact request or query.
4. **No glossary, no Section 0** beyond a one-line prerequisite list.
5. **Still one test per verifiable claim.** Speed is not a licence to merge three assertions into one
   checkbox: a merged test cannot be triaged when it fails.
6. **Push harder on the unhappy paths.** An expert can and should test the boundaries a novice cannot
   reach — token expiry, race conditions, concurrent edits, malformed payloads.

### Example

```markdown
### 2.2  Sign in with the test account
<!-- uat:test id=2.2 -->

- **Goal:** Password auth issues a valid session.
- **Steps:**
  1. `POST /api/auth/login` with `{"email":"tester@example.com","password":"demo-password-123"}`
     — or sign in through the UI at `/`.
- **PASS looks like:** `200`, response sets a `session` cookie with `HttpOnly` and `SameSite=Lax`,
  and `GET /api/me` with that cookie returns the user. The header renders the display name.
- **If it does not work:** Capture the response status, body, and `Set-Cookie` header, plus the
  server log line for the request.
```

---

## Choosing when the user is unsure

If the user cannot say which level applies, ask who will physically execute the checklist, then map:

- someone outside the engineering team, or anyone who would need help installing Docker → **Novice**
- a designer, PM, support engineer, or a developer from another team → **Intermediate**
- a developer or QA engineer who could debug a failure themselves → **Expert**

When two people of different levels will share one run, write for the lower level. The higher-level
tester can skim; the lower-level one cannot fill in a gap.
