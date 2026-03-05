---
intent: <slug>
version: "1.0.0"
priority: critical | high | medium | low
domain: <domain>
changelog:
  - "1.0.0: Initial spec"
---

## IntentSpec: <Title>

### Objective
<!-- What user problem are you solving? Ground it in evidence. -->
[Support ticket / metric / user quote that motivated this]

### User Goal
As a [user type], I need to [accomplish X] so that [outcome Y].

### Outcomes (Verifiable)
- [ ] Metric A moves from X to Y (measured via [method])
- [ ] Feature B behaves like [specific behavior] in [specific scenario]
- [ ] Error rate for C drops below D% for 7 consecutive days

### Constraints
- Must maintain backward compatibility with [API version / data schema]
- Must not increase p95 latency above [threshold]
- Must pass existing test suite without modifications to tests

### Edge Cases
- When [condition]: [expected behavior]
- When [condition]: [escalate to human / fail gracefully]

### Goal Hierarchy
<!-- Override project defaults if this task has specific priorities -->
1. [Top priority for this task]
2. [Second priority]
3. [Third priority]

### Conflict Resolution
If [goal A] vs [goal B] conflict: [which wins]. Flag trade-off in PR description.

### Escalation Triggers
- [Condition requiring human input]
- [Condition requiring human input]

### Verification
- Automated: `[command that proves success]`
- Manual: [QA checklist or review step]
- Metric: [Observable measurement over time]
