# The checklist file

One JSON file describes one checklist. `scripts/build-checklist.mjs` checks it and turns it into the
web page. `example-checklist.json` is a complete working example.

## Top level

| Field | Required | What it is |
|---|---|---|
| `title` | yes | The task in the reader's words. "Save your work and send it to GitHub", not "Commit and push". |
| `summary` | yes | Two or three sentences: what these steps achieve, and how the reader will know they are finished. |
| `steps` | yes | The steps, in the order they are done. See below. |
| `source` | no | Where the task came from: "GitHub issue #494: Login button does nothing". |
| `sourceUrl` | no | A link for `source`. Must start with `http://`, `https://` or `mailto:`. |
| `minutes` | no | A whole number: your honest estimate for the whole list. |
| `before` | no | A list of things to have ready before step 1 (a window open, a password to hand, an account). |
| `words` | no | A list of `{ "word", "meaning" }` pairs for every technical word the steps could not avoid. |

## Each step

| Field | Required | What it is |
|---|---|---|
| `title` | yes | A short command: "Open the Settings page". Every title must be different. |
| `do` | yes | Exactly what to do: where to look, what to click or type, which key to press. |
| `why` | yes | The hover note: why this step exists, as an everyday comparison. |
| `paste` | no | `{ "text", "into" }`. Text the reader copies with one button, and the place it goes ("the Claude Code window", "the terminal", "the Name box"). |
| `expect` | no | What appears when the step worked. Leave it out only when nothing visible changes. |
| `stuck` | no | The most likely way this step goes wrong, and what to do about it. |
| `warning` | no | Shown above the step. Use it for anything that cannot be undone, costs money, or is seen by others. |
| `group` | no | A heading such as "Part 1: Get ready". Consecutive steps with the same `group` share one heading. |

## Formatting inside text

Text fields understand three things and nothing else:

- `` `backticks` `` for anything typed or read exactly
- `**bold**` for the name of a button, key or menu item
- `[words](https://example.com)` for a web link

A blank line starts a new paragraph. `paste.text` is never formatted: it is copied exactly as written.

## Rules the script enforces

The script stops with a `Checklist problem:` message when:

- the file is missing or is not valid JSON
- `title`, `summary`, or a step's `title`, `do` or `why` is missing or empty
- there are no steps, or more steps than one page holds (split the task into two checklists)
- two steps have the same title
- `minutes` is not a whole number, or `sourceUrl` is not a web or mail link
- `paste` is missing its `text` or its `into`

Fix the file and run the script again.

## Ticks

The page remembers ticks in the reader's browser, under the page's file name. Build a revised
checklist to the same file name and the ticks for steps whose titles did not change are kept.
