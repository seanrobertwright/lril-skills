# Report schema

`scripts/render-report.mjs` validates this JSON and refuses to render until every problem is fixed. Every field is required unless marked optional. Arrays may be empty unless stated.

```json
{
  "repo": {
    "owner": "acme",
    "name": "widget",
    "sha": "<full 40-character commit SHA>",
    "analyzedAt": "2026-11-05",
    "visibility": "public",
    "relationship": "original",
    "upstream": "https://github.com/parent/widget",
    "subpath": "packages/foo",
    "noDivergence": false
  },
  "summary": "Two sentences: the current method and tools.",
  "narrative": ["One paragraph per entry."],
  "limitations": ["What could not be determined, and why."],
  "history": { "quality": "full" },
  "coverage": { "commitsScanned": 1200, "prsSampled": 60, "prsTotal": 410, "gh": "available" },
  "eras": [
    {
      "name": "Spec-driven with Claude Code",
      "from": "2026-03-01",
      "to": null,
      "current": true,
      "summary": "What defines this era.",
      "classification": [
        {
          "category": "framework",
          "finding": "SpecKit drives feature work.",
          "label": "Used",
          "citations": [{ "text": "abc1234", "url": "https://github.com/acme/widget/commit/abc1234" }]
        }
      ]
    }
  ],
  "workflow": [
    { "stage": "spec", "tool": "SpecKit", "label": "Used", "citations": [{ "text": "specs/001", "url": "https://github.com/acme/widget/tree/<sha>/specs/001" }] }
  ],
  "practices": [
    {
      "title": "Specs change in the same PR as code",
      "what": "What they do.",
      "why": "Why it seems to work.",
      "cost": "What adopting it takes.",
      "label": "Enforced",
      "citations": [{ "text": "#412", "url": "https://github.com/acme/widget/pull/412" }]
    }
  ],
  "inherited": [{ "item": ".cursor/rules", "source": "the starter template" }],
  "unknownTools": [{ "path": ".foo/", "note": "What it appears to be." }],
  "suspected": [{ "pattern": "Uniform commit subjects from 2025 on", "note": "Fits agent use, and also a strict convention." }],
  "steeringAttempts": [{ "path": "AGENTS.md", "excerpt": "The quoted text." }],
  "blindSpots": ["At least one entry, always."],
  "skillMapping": [{ "practice": "Specs change with code", "status": "Partial", "skill": "to-spec", "note": "Writes specs but does not gate PRs." }]
}
```

## Allowed values

| Field | Values |
|---|---|
| `repo.visibility` | `public`, `private` |
| `repo.relationship` | `original`, `fork`, `template`, `mirror` |
| `history.quality` | `full`, `thin` |
| `coverage.gh` | `available`, `unavailable`, `rate-limited` |
| `category` | `method`, `framework`, `agent`, `skill`, `mcp`, `review`, `ci`, `other` |
| `label` | `Enforced`, `Used`, `Present` (practices: `Enforced`, `Used`) |
| `workflow[].stage` | `spec`, `plan`, `code`, `test`, `review`, `merge`, `release` |
| `skillMapping[].status` | `Covered`, `Partial`, `Gap` |

## Rules the script enforces

- `repo.upstream`, `repo.subpath`, and `repo.noDivergence` are optional. `noDivergence: true` needs an `upstream` URL and allows `eras` to be empty.
- Dates are real `YYYY-MM-DD` dates. `sha` is the full 40-character hash.
- Exactly one era has `current: true`, and that era has `to: null`. Every other era has a `to` date.
- Every classification, workflow stage, and practice has at least one citation. Each citation has `text`, and an optional `url`. A URL that is not http or https renders as plain text.
- `workflow` holds each stage at most once, so combine tools in one `tool` string. Use `tool: null` when a stage has evidence but no named tool. Input order is ignored: the script sorts stages canonically.
- With `history.quality: "thin"`, no finding, stage, or practice can be `Used`.
- `limitations` must be non-empty when history is thin or `coverage.gh` is not `available`.
- `blindSpots` must be non-empty.
- `skillMapping[].skill` is required unless the status is `Gap`.
- No string anywhere may contain an email address. Rephrase a quote that holds one, for example `Co-Authored-By: Claude`.

## Diagram

The script draws the animated diagram when `workflow` has at least two stages. With fewer, the report says why in place of the diagram, so leave a stage out rather than padding the list to reach the threshold.
