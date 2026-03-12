# ADR 0005: External Calendar Editability Rules

## Status

Accepted

## Date

2026-03-10

## Decision

External calendar integrations in ZoesCal and ZoesTM must follow explicit editability rules based on source ownership.

Imported external calendar objects are not automatically fully editable local objects.

The system must distinguish between:

- provider-owned fields
- app-owned overlay fields
- shared fields only where explicitly supported
- read-only mirrored data

This applies to integrations such as:

- Google Calendar
- CalDAV
- future external calendar providers

The default rule is:

> external calendar data remains owned by the provider unless the integration explicitly supports safe bidirectional editing for specific fields.

---

## Why this exists

Calendar integrations are high-value, but they are also one of the easiest ways to corrupt user trust.

If imported events are treated like fully local records without ownership rules, the product will eventually create:

- edits that appear to save but are later overwritten
- provider data corruption
- duplicate events
- invisible sync failures
- confusion about what can be changed where

Users need predictable behavior.

The system needs to know the difference between:

- “this event is mirrored here”
- “this event can be safely edited here”
- “this local note belongs only to our app”
- “this provider owns the canonical schedule”

---

## Core principle

External events are mirrors first, editable objects second.

Editability must be granted intentionally, field by field, based on provider capability and product policy.

Do not assume that because an event is visible in the app, it is fully editable in the app.

---

## Ownership model

## External provider owns

For provider-backed events, the external calendar provider is the default source of truth for canonical event data.

Typically provider-owned fields include:

- external event identity
- start time
- end time
- all-day state
- attendee list
- organizer
- provider calendar placement
- recurrence metadata
- provider meeting links
- cancellation state

These fields must not be treated as app-owned unless explicit integration rules allow it.

---

## App may own overlays

ZoesCal or ZoesTM may store app-local overlays that do not overwrite provider truth.

Examples of app-local overlays:

- private local notes
- color/view preferences
- pinned state
- workflow linkage to internal tasks
- local reminder overlays
- local tags not supported by provider
- derived scheduling metadata

Overlay data must be stored separately from provider-owned canonical fields.

Do not write app-only overlay meaning back into provider event fields just because a field exists.

---

## Editability classes

Each imported external event should resolve to one of these classes.

### 1. Read-only mirror

The event is visible locally but canonical fields cannot be edited from the app.

Allowed examples:
- add local note overlay
- link event to internal task
- add local reminder overlay if supported
- adjust display preferences

Not allowed:
- changing provider-owned time
- changing attendees
- changing organizer-owned metadata

This should be the safest default.

---

### 2. Limited editable mirror

Some provider-backed fields may be edited locally and synced back because provider capability and policy allow it.

Possible allowed fields:
- title
- description
- start/end time
- location

Possible disallowed fields:
- organizer
- attendee permissions
- provider-specific recurrence fields
- unsupported conferencing metadata

Allowed fields must be explicitly defined per provider and permission context.

---

### 3. Locally managed exported event

An event created locally in ZoesCal may later be exported to an external calendar.

In that case, ownership policy must still remain clear.

Recommended default:
- local event keeps canonical internal identity
- provider copy is linked via source metadata
- provider-editable status depends on export policy
- sync rules must define whether local app remains primary owner or whether ownership becomes shared/provider-led

Do not leave this ambiguous.

---

## Default product policy

Until a provider integration has proven bidirectional editing safely, imported external events should start as:

- read-only mirror for provider-owned fields
- app-editable only for local overlays

This is slower, but safer.

It is better to expand editability later than to promise full editing and silently break user data.

---

## Required metadata

Every external-backed event must carry enough metadata to determine editability.

Minimum useful fields:

- `id`
- `source.type`
- `source.instanceId`
- `source.externalId`
- `source.originApp`
- `readOnly`
- `editabilityClass`
- `providerCapabilities`
- `lastSyncedAt`
- `syncStatus`

Helpful additional fields:

- `providerCalendarId`
- `hasLocalOverlay`
- `canEditTime`
- `canEditTitle`
- `canEditDescription`
- `canEditAttendees`
- `canDelete`
- `recurrenceEditMode`

The system should not infer permissions from vibes or UI assumptions.

---

## Field-level rules

## Title

Default:
- provider-owned for imported events

Policy:
- editable only when provider permissions allow it and integration supports it safely

If not editable:
- local “renaming” must be stored as display overlay only if product intentionally supports that
- otherwise block the edit

---

## Description

Default:
- provider-owned for imported events

Policy:
- may be editable for some providers
- app-local notes should not overwrite provider description unless explicitly intended

Preferred approach:
- keep app notes separate from provider description

---

## Start and end time

Default:
- provider-owned

Policy:
- editable only when integration supports true write-back for this event and permission context
- if local drag/drop is not allowed, UI must make that clear

Do not allow draggable time changes in the UI if the event is effectively read-only.

---

## All-day state

Default:
- provider-owned

Policy:
- same as time edits
- do not treat all-day conversion as harmless cosmetic change

---

## Attendees and organizer data

Default:
- provider-owned

Policy:
- highly restricted
- only editable if provider integration explicitly supports it and account permissions allow it

Do not model attendee editing as generic event editing.

---

## Recurrence

Default:
- provider-owned and high-risk

Policy:
- recurrence should be considered advanced editability
- imported recurring series should initially be read-only unless recurrence editing is deliberately implemented

Reason:
recurrence rules are one of the fastest ways to create broken sync.

---

## Deletion

Default:
- imported provider-backed events should only be deletable locally if the integration supports real provider deletion and permissions allow it

Otherwise:
- offer hide/detach/local ignore behavior instead of fake deletion

Never pretend deletion worked if it only removed the local mirror temporarily.

---

## Color and display styling

Provider event colors may be mirrored.
App-local display styling may also exist.

Rule:
- visual customization should not rewrite provider event color unless explicitly intended and supported
- skin/theme presentation is separate from provider event color metadata

---

## Task linkage

Imported external events may link to internal tasks or scheduled logic.

Rule:
- linkage is app-owned overlay data
- linking an event to a task does not transfer ownership of the event to ZoesTM or ZoesCal
- deleting a task must not destroy provider event data
- deleting a provider event must not silently destroy the task unless explicit product logic says so

---

## Reminder overlays

External providers may already have reminders.

ZoesCal or ZoesTM may also want local reminder behavior.

Rule:
- provider reminders and local reminders must be distinguishable
- a local reminder overlay must not be assumed to exist in the provider
- modifying local reminders must not silently rewrite provider reminder settings unless explicitly supported

---

## UI rules

The UI must communicate editability honestly.

### Required behavior

- read-only events must look read-only in edit flows
- disabled controls should match actual sync capability
- drag/drop should be blocked when time edits are not allowed
- provider-owned fields should not look like guaranteed local edits if they are not
- local overlays should be visually distinguishable where necessary

### Good examples

- read-only badge
- “Managed by Google Calendar” note
- separate local notes section
- disabled attendee editor
- limited-edit explanation in event details

### Bad examples

- editable form that later silently reverts
- draggable event that snaps back after sync with no explanation
- delete button that only hides local state but implies provider deletion

---

## Sync rules

When syncing imported provider events:

1. match by provider identity first
2. preserve canonical internal ID
3. preserve provider-owned fields from source
4. apply app-local overlays separately
5. only write back allowed fields
6. reject or log blocked writes explicitly

Do not merge provider-owned and app-owned data into one ambiguous blob.

---

## Conflict handling

Conflicts involving external events should follow provider ownership first.

### Examples

#### Local app changes provider-owned time on read-only event
- reject local mutation
- keep provider value
- optionally show blocked-edit message
- not necessarily a full conflict unless user action is needed

#### Provider changes title while app changes local note
- merge safely
- provider title updates
- local note remains

#### Provider deletes event while app adds local overlay
- provider deletion wins for event existence
- local overlay may be dropped or preserved in audit/tombstone form according to policy

#### Duplicate local mirrors point to same provider event
- mark integrity conflict
- stop unsafe automatic merge

---

## Offline behavior

Offline mode must still obey ownership.

If the user edits a provider-owned read-only field offline:

- queueing that mutation as guaranteed sync is incorrect
- either block the edit locally or mark it clearly as non-syncable pending discard/review

Do not let offline mode imply permissions that do not exist.

---

## Provider capability matrix

Each provider integration should maintain an explicit capability matrix.

Example categories:

- can read events
- can create events
- can edit title
- can edit description
- can edit time
- can edit recurrence
- can edit attendees
- can delete events
- can manage reminders
- can read/write conference data

The UI and sync engine should both depend on this capability layer.

Do not hardcode assumptions like “all calendar providers support the same edits.”

---

## Recommended rollout

Implement external calendars in this order:

1. import and display
2. read-only mirror correctness
3. local overlays
4. limited editable fields
5. deletion rules
6. recurrence and advanced provider features only later

This reduces the risk of early sync disasters.

---

## Non-goals

This ADR does not define:

- exact OAuth or auth flows
- exact provider API adapters
- exact recurrence editing UI
- exact local overlay schema
- exact notification backend
- advanced cross-provider migration behavior

Those can be defined later.

---

## Alternatives considered

### Alternative A: Treat imported events like fully local editable events

Rejected.

Reason:
This creates false expectations and high risk of provider sync breakage.

---

### Alternative B: Make all imported events permanently read-only with no overlays

Rejected.

Reason:
Too restrictive.
Useful local augmentation like notes, reminders, and task linkage should still be possible.

---

### Alternative C: Use one generic editability policy for all providers

Rejected.

Reason:
Providers differ in permissions, APIs, and field support.

---

### Alternative D: Hide ownership details from the user

Rejected.

Reason:
That causes confusing reversions and destroys trust when edits do not persist.

---

## Consequences

### Positive

- clearer user expectations
- safer provider sync
- fewer fake edits and silent reversions
- better foundation for future bidirectional editing
- cleaner separation between external truth and app-local enhancement

### Costs

- more metadata and UI work
- more provider-specific logic
- more disciplined field ownership handling
- slower rollout for advanced editing features

---

## Implementation guidance

Minimum implementation steps:

1. add editability class to imported events
2. separate provider-owned fields from local overlays
3. block UI edits for unsupported fields
4. add provider capability matrix
5. enforce write-back only for explicitly supported fields
6. log blocked writes and integrity issues
7. start with read-only mirrors before limited editable sync

---

## Final statement

External calendar events are not automatically local objects.

Provider truth stays with the provider.
App value comes from safe overlays and explicit editability rules.

That boundary is what makes integrations trustworthy.
