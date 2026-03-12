mkdir -p shared/decisions

cat > shared/decisions/0001-zoescal-zoestm-split.md <<'EOF'
# ADR 0001: Split ZoesCal and ZoesTM into Separate Products with a Shared Contract

## Status

Accepted

## Date

2026-03-10

## Decision

We will build **ZoesCal** and **ZoesTM** as two separate but connected products.

- **ZoesCal** is the calendar, planning, and scheduling surface
- **ZoesTM** is the deeper productivity and workbench engine
- the two products will sync through a **shared contract**
- shared entities include tasks, events, scheduled blocks, reminders, source metadata, and sync metadata
- visual theming in ZoesCal will use a **token-based skin system**
- skins affect presentation only, never behavior

---

## Context

The original product direction risked collapsing multiple jobs into one application:

- calendar UI
- planning and scheduling
- deep task/workflow management
- heavier desktop-first power features
- future integrations
- customization/theming

That approach would likely create a product that is:

- harder to reason about
- harder to scale across platforms
- harder to theme cleanly
- harder to sync with external services
- more likely to blur ownership of data and behavior

There is also a clear product distinction emerging:

### ZoesCal

A cross-platform calendar/planning product for:

- calendar views
- time blocking
- scheduling
- reminders
- beautiful UI
- strong integrations
- visual customization

Target platforms:

- web
- mobile
- desktop

### ZoesTM

A desktop-first productivity/workbench product for:

- deeper workflow logic
- richer task handling
- heavier local-first features
- power-user workflows
- future advanced orchestration

Target platforms:

- Windows
- macOS
- Linux

Trying to force both into one primary application would make the boundaries unclear and increase implementation risk.

---

## Why this decision was made

### 1. Different products have different centers of gravity

ZoesCal is centered on time, planning, and presentation.

ZoesTM is centered on execution, workflow depth, and local-first power features.

These are related, but they are not the same product.

---

### 2. A shared contract is safer than shared assumptions

If both apps exchange data through an explicit contract, then:

- sync behavior can be reasoned about
- ownership can be defined
- conflicts can be handled deterministically
- integrations can be added without rewriting both apps around hidden assumptions

Without a contract, coupling will spread through internal app behavior and create fragile sync.

---

### 3. ZoesCal must not become “ZoesTM with a calendar tab”

If the split is not enforced early, the calendar product will slowly absorb:

- workflow-specific logic
- desktop-only assumptions
- deeper engine concerns
- complicated state rules that belong elsewhere

That would damage the usability and portability of ZoesCal.

ZoesCal should remain a strong standalone planning product even when ZoesTM is not present.

---

### 4. ZoesTM should not be constrained by calendar-first design

ZoesTM needs room for:

- heavier interaction models
- desktop-first workflows
- richer task/process state
- local-first behavior
- advanced automation later

If it is built as a subordinate module inside a calendar-first app, it will inherit the wrong constraints.

---

### 5. Theming must stay cosmetic

ZoesCal is intended to support 9 built-in skins and user-extensible CSS skins.

That is only maintainable if theming is handled through semantic tokens and not through behavior forks.

If skins are allowed to leak into component logic, the UI becomes harder to maintain and test.

---

## What this means in practice

### Product boundary

ZoesCal owns:

- calendar presentation
- schedule visualization
- time blocking UX
- reminder-oriented planning surfaces
- theme/skin presentation system
- calendar-centric integrations

ZoesTM owns:

- deeper task/workflow logic
- richer productivity engine behavior
- heavier local-first features
- desktop-first advanced workflows
- power-user execution surfaces

---

### Integration boundary

The apps sync through shared models rather than direct UI coupling.

The shared contract must define at least:

- task
- event
- scheduled block
- reminder/alarm
- source metadata
- sync metadata
- ownership expectations
- conflict behavior
- stable ID rules

---

### Ownership expectations

Default ownership should be practical, not ideological.

Typical expectations:

- tasks are primarily ZoesTM-owned
- scheduled blocks are shared bridge objects
- calendar events are usually ZoesCal-managed or external-provider-owned
- reminders belong to the creating app unless tied to provider behavior

This prevents “everything edits everything” chaos.

---

### Skin system expectations

ZoesCal skins must be:

- token-based
- swappable
- presentation-only
- safe for user extension via CSS

Skins may change:

- colors
- radii
- shadows
- motion feel
- typography
- density within limits

Skins must not change:

- sync behavior
- feature access
- shortcuts
- edit rules
- drag/drop semantics
- data model meaning

---

## Consequences

### Positive consequences

- clearer architecture
- cleaner platform targeting
- easier staged implementation
- safer sync design
- better maintainability
- better theming extensibility
- easier future integrations
- less risk of UI logic becoming tangled with workflow engine rules

### Negative consequences

- requires explicit sync design early
- requires more upfront documentation
- creates two app codebases instead of one
- shared contract changes must be managed carefully
- some features may need coordination across products instead of single-app shortcuts

---

## Tradeoffs accepted

We are intentionally accepting:

- more structure now
- more boundary work now
- more contract design now

to avoid:

- uncontrolled coupling later
- broken sync semantics later
- theme/logic entanglement later
- platform confusion later
- calendar UX being distorted by power-user engine concerns

---

## Alternatives considered

### Alternative A: One app with everything inside it

Rejected.

Reason:
This would blur responsibilities, increase coupling, and make both the calendar experience and the deeper workflow engine worse.

### Alternative B: ZoesTM as the main app, ZoesCal as a thin view layer

Rejected.

Reason:
This would make ZoesCal too dependent on ZoesTM internals and weaken its ability to stand alone as a calendar/planning product.

### Alternative C: ZoesCal as the main app, ZoesTM as a plugin/module

Rejected.

Reason:
This would force the deeper productivity engine into calendar-first assumptions and limit desktop-first power design.

### Alternative D: Shared database/schema first, contract later

Rejected.

Reason:
A schema without a product-level ownership model is not enough. The real issue is not just storage shape, but edit rules, sync semantics, and conflict behavior.

---

## Implementation direction

The implementation order following this decision is:

1. define shared core models
2. define source-of-truth and conflict rules
3. scaffold ZoesCal as a standalone product
4. build internal scheduling flow first
5. sync ZoesCal with ZoesTM through the contract
6. add external calendar integrations after internal semantics are stable
7. add secondary integrations later based on workflow value

---

## Non-goals

This decision does not define:

- the final sync transport layer
- the final database/storage engine
- the full notification architecture
- the full mobile implementation plan
- the multi-agent workflow system
- final integration priority beyond staged direction

Those should be decided in later ADRs.

---

## Follow-up documents

This ADR depends on or should be followed by:

- `shared/contracts/core-model.md`
- `shared/sync/source-of-truth.md`
- `ZoesCal/docs/ux/skin-system.md`
- `ZoesCal/docs/plans/phases.md`

Suggested next ADRs:

- `0002-stable-id-strategy.md`
- `0003-sync-conflict-resolution.md`
- `0004-zoescal-skin-token-architecture.md`
- `0005-external-calendar-editability-rules.md`

---

## Final statement

We are splitting the system on purpose.

ZoesCal should be excellent at planning, calendar interaction, scheduling, and visual customization.

ZoesTM should be excellent at deeper productivity workflows and desktop-first power use.

They should work together through a clear contract, not through accidental coupling.
EOF
