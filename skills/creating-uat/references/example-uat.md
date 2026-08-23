# Demo App — User Acceptance Test

<!-- uat:meta
version: 1
app: Demo App
generated: 2026-08-23
tester_level: novice
commit: abc1234
branch: main
-->

## How to use this checklist

Work top to bottom and do not skip a section — later tests assume the earlier ones passed.

- A **terminal** is the black window where you type commands. Section 1 shows you how to open one.
- Copy commands exactly, including every dash and slash.
- If something goes wrong, write down the **exact** words you see, and add a picture if you can.

## Words used in this document

- **Terminal** — the black window where you type commands.
- **Docker** — a program that runs the app's database for you.
- **Address bar** — the wide box at the very top of your web browser where web addresses go.

## Section 1 — Setting up
<!-- uat:section id=1 title="Setting up" -->

### 1.1  Check that Docker is installed
<!-- uat:test id=1.1 -->

- **Goal (plain words):** Make sure the program that runs the app's database is on your computer.
- **Before you start:** Nothing — this is the first test.
- **Steps:**
  1. Press the **Windows** key on your keyboard.
  2. Type `powershell` and press Enter. A black window opens. This is the terminal.
  3. Type exactly this and press Enter: `docker --version`
  4. Wait about two seconds.
- **PASS looks like:** A line appears starting with `Docker version` followed by numbers, for example
  `Docker version 27.1.1`.
- **If it does not work:** If you see `not recognized`, Docker is not installed. Mark this Fail and
  write down what you saw — do not carry on to test 1.2.

### 1.2  Start the app
<!-- uat:test id=1.2 -->

- **Goal (plain words):** Turn the app on.
- **Before you start:** Test 1.1 passed.
- **Steps:**
  1. In the same terminal, type `cd C:\Projects\demo-app` and press Enter.
  2. Type `docker compose up -d` and press Enter.
  3. Wait. This can take two or three minutes the first time. Lines of text will scroll past.
  4. Stop waiting when the typing cursor comes back and nothing new appears.
- **PASS looks like:** The last lines contain the words `Started` or `Running`, and there is no red
  text saying `error`.
- **If it does not work:** Copy the last ten lines of text into the box below.

## Section 2 — Using the app
<!-- uat:section id=2 title="Using the app" -->

### 2.1  Open the home page
<!-- uat:test id=2.1 -->

- **Goal (plain words):** Look at the app in your web browser.
- **Before you start:** Test 1.2 passed and the terminal is still open.
- **Steps:**
  1. Open your web browser (Chrome, Edge or Firefox).
  2. Click the address bar at the very top.
  3. Type `http://localhost:3000` and press Enter.
- **PASS looks like:** A page appears with the words **Welcome to Demo App** near the top and a blue
  **Sign in** button on the right.
- **If it does not work:** If the page says "can't be reached", go back to test 1.2. Take a picture
  of the screen and attach it below.

### 2.2  Sign in with the test account
<!-- uat:test id=2.2 -->

- **Goal (plain words):** Get into the app using the practice account.
- **Before you start:** Test 2.1 passed.
- **Steps:**
  1. Click the blue **Sign in** button in the top-right corner.
  2. Click the box labelled **Email** and type `tester@example.com`
  3. Click the box labelled **Password** and type `demo-password-123`
  4. Click the blue **Continue** button.
- **PASS looks like:** The page changes and your name appears in the top-right corner instead of the
  Sign in button.
- **If it does not work:** Write down any red message that appears under the boxes.

### 2.3  Signing in with the wrong password is refused
<!-- uat:test id=2.3 -->

- **Goal (plain words):** Check the app does not let someone in with a wrong password.
- **Before you start:** Test 2.2 passed. Click your name in the top-right, then click **Sign out**.
- **Steps:**
  1. Click **Sign in** again.
  2. Type `tester@example.com` in the Email box.
  3. Type `this-is-wrong` in the Password box.
  4. Click **Continue**.
- **PASS looks like:** You are NOT let in. A message appears saying **Email or password is
  incorrect**. The page does not show your name in the corner.
- **If it does not work:** If you are let in, this is a serious problem — mark it Fail and say so.

## Not in scope (deferred — do NOT test)

- **Sending email** — not built yet. The app will never send you a message.
- **Mobile phone layout** — deliberately left for a later release.

## Sign-off

- Tester name: ____________________  Date: ____________
