# Intent Engine (Full)

This repo is a **Claude Skill bundle** + a small local demo runner.

It implements a reusable pattern:

1) **Structured Intent**
2) **Executable Plan**
3) **Verification Report**

And it adds **Personal Intent Awareness** so the engine can align the plan with what the user is optimizing for (ship vs learn vs stabilize vs de-risk, etc.).

## Files

- `SKILL.md` — Claude Skill entrypoint (instructions + contract)
- `resources/intent.schema.json` — JSON Schema for output contract
- `resources/plugin-interface.md` — domain plugin contract + tool keys
- `resources/domain-catalog.md` — domains overview
- `resources/intent-examples.md` — examples including personal intent
- `resources/personal-intent.md` — personal intent reference
- `resources/plugins/*.plugin.md` — domain plugin specs (ports, ehs)
- `scripts/*.py` — placeholder scripts for compilation/validation/demo

## Quick demo

```bash
echo "Fix my port conflicts" | python scripts/run_intent_engine.py
```

## Notes
This is a **template/spec bundle**. To make it “real,” you’ll map plan step tool keys
to actual implementations (CLI scripts, APIs, repo tools) and implement validators.
