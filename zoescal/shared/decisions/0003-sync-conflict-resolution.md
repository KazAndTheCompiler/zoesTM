# ADR 0003: Sync Conflict Resolution for Shared Objects

## Status

Accepted

## Date

2026-03-10

## Decision

ZoesCal and ZoesTM will use deterministic conflict handling for shared objects.

Conflicts must never be silently ignored, silently overwritten, or “best guessed” when ownership rules already define what should happen.

The sync system must:

- apply ownership rules first
- apply editability rules second
- use deterministic merge behavior for shared fields
- mark explicit conflict state when rules do not resolve safely
- preserve enough conflict data for repair, logging, and user-visible handling when needed

This applies to:

- tasks
- events
- scheduled blocks
- reminders
- future shared objects added to the contract

---

## Why this exists

The system will have concurrent changes from multiple places:

- ZoesCal
- ZoesTM
- external calendar providers
- future integrations
- offline edits syncing later

Without a conflict strategy, sync becomes random.

That produces:

- disappearing edits
- duplicated objects
- wrong schedule state
- provider data corruption
- user distrust

Conflict resolution is not a nice extra.
It is part of the product’s data integrity model.

---

## Core principle

A conflict is not “two things changed.”

A conflict is:

> two or more valid-looking mutations that cannot be safely merged under the ownership and editability rules.

Many simultaneous edits are not real conflicts.
They are resolved automatically by the rules below.

---

## Resolution order

All sync processing should evaluate changes in this order:

1. validate object identity
2. validate object type
3. validate ownership and editability
4. apply deterministic merge rules
5. mark conflict only if safe merge is not possible
6. preserve conflict snapshot and reason

This order matters.
Do not jump straight to timestamp comparison before ownership rules are checked.

---

## Conflict classes

### 1. Ownership violation

A non-owner attempts to modify owner-only fields.

Example:
- ZoesCal attempts to modify deep task metadata owned by ZoesTM

Default action:
- reject field mutation
- preserve owner value
- log reason
- only mark conflict if the attempted edit needs user attention

---

### 2. Read-only source violation

A local app attempts to edit fields controlled by an external provider or read-only object.

Example:
- imported Google Calendar event time is changed locally even though provider sync marks it read-only

Default action:
- reject mutation
- keep provider-owned value
- mark sync note or conflict depending on UX severity

---

### 3. Concurrent shared-field edit

Two systems edit a field that is allowed to be shared.

Example:
- ZoesCal moves a scheduled block
- ZoesTM also moves the same scheduled block before sync settles

Default action:
- attempt deterministic merge rule
- if merge rule cannot decide safely, mark conflict

---

### 4. Delete-vs-update conflict

One system deletes an object while another updates it.

Example:
- ZoesTM deletes a scheduled block
- ZoesCal edits its time offline

Default action:
- resolve using deletion policy and ownership rules
- if object is owner-deleted, do not silently resurrect
- preserve update snapshot for repair if needed

---

### 5. Provider remap or duplication conflict

Multiple local objects claim the same external source identity.

Example:
- two local mirrors point to the same Google Calendar event ID

Default action:
- stop automatic merge
- mark integrity conflict
- require deterministic repair path

---

### 6. Integrity conflict

Internal ID mismatch, broken links, or invalid payload.

Example:
- reminder points to missing target ID
- same internal ID appears for incompatible object meanings

Default action:
- reject sync mutation
- log integrity error
- do not try heuristic repair during normal sync

---

## Object-level guidance

## Tasks

Default owner: ZoesTM

### Usually owner-only fields
- title
- description
- status
- workflow metadata
- project linkage
- tags unless explicitly shared

### Usually shared or partially shared fields
- due date if contract allows
- linked scheduled blocks
- reminder associations depending on source

### Rule
If ZoesCal edits an owner-only task field, keep ZoesTM value unless later ADR explicitly broadens editability.

---

## Scheduled blocks

Default owner: shared, with creation origin affecting precedence

### Shared fields
- startAt
- endAt
- status
- title within limits
- task linkage with validation

### Rule
If both apps edit timing, use deterministic shared-field resolution.
If one app tries to detach task linkage in a way that breaks contract assumptions, mark conflict.

Scheduled blocks are the most likely real conflict surface and should receive the strongest logging.

---

## Events

Default owner:
- external provider for imported events
- ZoesCal for local calendar events unless otherwise exported

### Rule
Provider-owned fields may not be overwritten by local apps unless provider editability explicitly allows it.

Local overlays such as notes or display metadata should be stored separately where possible to avoid fake conflicts.

---

## Reminders

Default owner: creator app unless provider-controlled

### Rule
Reminder timing conflicts should prefer creator ownership unless reminder is merely derived from another object and should be regenerated instead of hand-merged.

---

## Deterministic merge rules

These rules should be used before marking a conflict.

## Rule 1: Owner wins for owner-only fields

If a field is owner-only, the owner value always wins.

Do not compare timestamps first.

---

## Rule 2: External provider wins for provider-owned fields

If a field belongs to a provider-owned event, provider value wins.

Do not silently write local value over it.

---

## Rule 3: Shared fields may use last-valid-write-wins

For truly shared fields, use last-valid-write-wins only after validating that:

- both edits are allowed
- neither edit violates object invariants
- the field is actually eligible for shared mutation

This is allowed for fields like:

- scheduled block start/end
- certain shared status markers
- presentation-neutral planning metadata

Last-valid-write-wins is a fallback, not the whole sync model.

---

## Rule 4: Delete is not automatically stronger than update

Delete-vs-update must respect ownership and tombstone policy.

Examples:
- owner delete usually wins
- non-owner delete may be rejected
- provider delete usually wins for provider mirrors
- local update may survive only if policy allows recreation or detach

---

## Rule 5: Preserve linkage invariants

A merge must not create invalid relationships.

Do not accept merges that create:

- reminder pointing to missing target
- scheduled block linked to nonexistent task
- imported event losing provider identity unexpectedly

If merge would break referential integrity, reject or mark conflict.

---

## Timestamps

Timestamps are useful but must not be the primary authority.

Use timestamps only after:

- identity is valid
- ownership is known
- editability is known
- field category is known

Reason:
a newer illegal edit should not beat an older legal edit.

---

## Conflict payload requirements

When a conflict is marked, preserve structured conflict metadata.

Minimum fields:

- `objectId`
- `objectType`
- `conflictReason`
- `localSnapshot`
- `incomingSnapshot`
- `detectedAt`
- `fieldDiffs`
- `owner`
- `sourceContext`

Optional helpful fields:

- `repairHint`
- `blockingSeverity`
- `relatedObjectIds`

---

## Sync status model

Objects should expose sync state that can represent conflict explicitly.

Example statuses:

- `local_only`
- `pending_sync`
- `synced`
- `conflict`
- `error`

Meaning:

- `conflict` = data is preserved, but auto-resolution stopped
- `error` = sync processing failed for technical or integrity reasons

Do not collapse these into one generic failure state.

---

## User-facing handling

Not every conflict should interrupt the user.

### Silent automatic resolution is acceptable when:
- rules clearly decide winner
- no user-authored data is lost unexpectedly
- object remains valid

### User-visible conflict handling is needed when:
- two valid user edits compete on shared fields
- deletion/update ambiguity matters
- object becomes partially blocked
- repair requires a choice
- the user’s expectation of what “won” is likely to differ from the automatic result

User-facing conflict UX should show:
- what changed
- which rule blocked automatic merge
- what options exist if manual repair is needed

---

## Logging requirements

Every real conflict should emit structured logs.

Minimum log content:

- object ID
- object type
- conflict reason
- winning side if any
- blocked side if any
- source systems involved
- whether user action is required

This is critical for debugging early sync behavior.

---

## Delete and tombstone policy

Deleted objects should retain tombstone metadata long enough for sync correctness.

Minimum tombstone properties:

- original internal ID
- deletedAt
- deletedBy
- deletionOrigin
- objectType

Why:
without tombstones, offline updates can accidentally recreate deleted objects as duplicates.

---

## Examples

### Example 1: Task title edited in both apps

- ZoesTM edits task title
- ZoesCal edits task title before sync

Rule:
- task title is ZoesTM-owned
- ZoesTM value wins
- ZoesCal mutation is rejected or logged as blocked edit
- not necessarily a user-visible conflict

---

### Example 2: Scheduled block moved in both apps

- ZoesCal moves block from 10:00 to 11:00
- ZoesTM moves same block from 10:00 to 12:00

Rule:
- timing is shared
- if no stronger invariant exists, apply last-valid-write-wins based on mutation ordering
- if ordering is ambiguous or merge policy requires explicit choice, mark conflict

---

### Example 3: Imported event edited locally

- Google Calendar event imported
- user tries changing event time in local view
- provider marks event read-only

Rule:
- provider-owned field wins
- local edit is blocked
- show limited editability explanation if needed

---

### Example 4: Task completed while future block is moved

- ZoesTM marks task complete
- ZoesCal moves a future linked block offline

Rule:
- task completion is owner-authoritative
- future block may need cancel-or-dim policy
- moved future block should not remain active as if task were incomplete
- if local block edit cannot be reconciled cleanly, mark conflict on block state, not task identity

---

### Example 5: Delete-vs-update on scheduled block

- ZoesCal deletes a block
- ZoesTM updates its title during delayed sync

Rule:
- check deletion ownership and block origin
- if delete is valid, keep tombstone and reject later update
- if delete was not allowed, restore object and apply valid update path

---

## Repair strategy

Normal sync should not do speculative repair.

If conflict exists:

- preserve both sides
- stop unsafe auto-merge
- expose deterministic repair path later

Repair tools may later:
- choose winner
- merge selected fields
- detach broken relationships
- rebind provider mapping
- recreate missing derived objects

But that is separate from the normal sync loop.

---

## Non-goals

This ADR does not define:

- the exact sync transport mechanism
- exact timestamp/vector clock implementation
- the full user interface for conflict repair
- the exact retention period for tombstones
- the exact storage schema for conflict snapshots

Those can be decided later as long as they obey these rules.

---

## Alternatives considered

### Alternative A: Last-write-wins for everything

Rejected.

Reason:
It ignores ownership, editability, provider rules, and integrity constraints.
It is simple but wrong for this product.

---

### Alternative B: Prompt the user for every conflicting change

Rejected.

Reason:
That creates too much friction and turns routine sync into constant interruption.

---

### Alternative C: Prefer one app globally

Rejected.

Reason:
Different object types have different ownership.
A single global winner would produce wrong behavior.

---

### Alternative D: Ignore blocked edits and never record them

Rejected.

Reason:
That hides real system behavior and makes debugging impossible.

---

## Consequences

### Positive

- predictable sync behavior
- safer multi-app editing
- clearer ownership enforcement
- reduced silent data loss
- stronger debugging and auditability
- better future integration safety

### Costs

- more sync code complexity
- need for structured logging
- need for conflict snapshot storage
- need for later repair UX/tooling

---

## Implementation guidance

Minimum implementation steps:

1. classify fields by owner-only, provider-owned, shared, or derived
2. enforce ownership checks before timestamp checks
3. add explicit `conflict` sync status
4. store conflict snapshots with reason codes
5. implement tombstones for deletions
6. add structured logs for all blocked merges and true conflicts
7. keep repair tooling separate from normal sync

---

## Final statement

Conflicts must be resolved by rules, not vibes.

Ownership decides first.
Editability decides second.
Merge rules decide third.

Only when those cannot safely decide should the system enter explicit conflict state.
