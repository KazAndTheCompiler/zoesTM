# ADR 0002: Stable ID Strategy for Shared Objects

## Status

Accepted

## Date

2026-03-10

## Decision

All shared objects exchanged between ZoesCal, ZoesTM, and future integrations must use stable internal IDs that are assigned once and never replaced.

This applies to:

- tasks
- events
- scheduled blocks
- reminders
- related shared objects added later

External provider IDs must be stored separately as source metadata and must never replace internal IDs.

---

## Why this exists

The system will have multiple producers and editors of data:

- ZoesCal
- ZoesTM
- external calendar providers
- future integrations like GitHub
- future internal automation or sync services

Without a stable ID strategy, the system will eventually create:

- duplicate records
- broken links between tasks and blocks
- bad merge behavior
- conflict resolution failures
- accidental record recreation after sync/import

IDs are the backbone of sync correctness.

---

## Core rules

### 1. Internal IDs are permanent

Once an internal ID is assigned to an object, it must never change.

Even if:

- the title changes
- the object moves between views
- the object syncs across apps
- the object is exported/imported again
- the external source changes its metadata

---

### 2. Internal IDs and external IDs are different things

Each shared object may contain:

- one internal canonical ID
- zero or more source/provider identifiers

Example:

- internal ID: `tsk_01JZ...`
- Google Calendar ID: stored as `source.externalId`
- local database row ID: implementation detail, not canonical identity

The canonical identity is always the internal ID.

---

### 3. IDs must not encode mutable meaning

Do not build IDs from:

- titles
- timestamps alone
- usernames
- project names
- platform-specific paths
- calendar names
- UI route fragments

Bad examples:

- `task-write-blog-post`
- `event-2026-03-10-0900`
- `zoescal-sidebar-item-4`

Those values can change and will break identity.

---

### 4. IDs must be generated at creation time

The app or service that creates the object assigns the internal ID immediately.

Creation must not depend on:

- a later sync roundtrip
- a database autoincrement from another system
- an external provider response
- UI hydration timing

This prevents temporary fake IDs from leaking into sync.

---

### 5. Links between objects must use internal IDs

Relationships must point to internal IDs.

Examples:

- scheduled block references task by `taskId`
- reminder references object by `targetId`
- sync conflict snapshots reference canonical internal ID

Do not link shared objects together using provider IDs.

---

## Recommended format

Use opaque string IDs with a type prefix.

Examples:

- `tsk_<opaque>`
- `evt_<opaque>`
- `blk_<opaque>`
- `rem_<opaque>`

The opaque part should be generated with a collision-resistant strategy such as:

- UUIDv7
- ULID
- another monotonic or high-entropy unique ID format

Preferred direction:

- human-recognizable type prefix
- opaque globally unique suffix
- sortable-by-time if practical, but not required for correctness

Example shape:

- `tsk_01K4ABCDEF1234567890XYZ`
- `blk_01K4ABM8M12N3P4Q5R6S7T`

Exact implementation format may vary, but the rules above may not.

---

## Why prefixes are useful

Prefixes are not identity by themselves, but they help with:

- debugging
- logs
- contract readability
- quicker inspection during sync issues
- safer cross-type validation

They make it easier to tell when a task ID is incorrectly placed in an event field.

---

## Source metadata model

Every shared object should carry source metadata separate from identity.

Example shape:

- `id`: canonical internal ID
- `source.type`: where it came from
- `source.instanceId`: app/install/account instance
- `source.externalId`: provider identifier if any
- `source.originApp`: original creation surface

This allows one object to remain the same object even when mirrored across systems.

---

## Creation ownership

The system that creates the object creates the internal ID.

### Examples

#### Task created in ZoesTM

- ZoesTM assigns `id`
- ZoesCal receives and uses the same `id`

#### Scheduled block created in ZoesCal

- ZoesCal assigns `id`
- ZoesTM receives and uses the same `id`

#### External event imported from Google Calendar

Two valid patterns exist:

##### Pattern A: local mirror object with internal ID
- create internal `evt_...`
- store Google event ID in `source.externalId`

##### Pattern B: deterministic adoption layer
- still expose one canonical internal `evt_...`
- retain provider ID only as provider metadata

In both cases, provider ID does not become the canonical shared ID.

---

## Import and deduplication rules

When importing from external systems, deduplication must check provider identity before creating a new internal object.

Minimum dedupe inputs:

- `source.type`
- `source.instanceId`
- `source.externalId`

If a matching provider-backed object already exists:

- update the existing internal object
- do not create a second object with a new internal ID

If no match exists:

- create a new internal object
- assign a new internal ID
- bind provider metadata to it

---

## Cross-app sync rules

When ZoesCal and ZoesTM sync:

- they must preserve internal IDs exactly
- neither app may “upgrade” or “normalize” the other app’s IDs into new ones
- receiving an object with a known internal ID means update, not recreate
- receiving the same payload twice should be idempotent

Stable IDs are required for idempotent sync.

---

## Conflict rules related to IDs

ID conflict means something has gone badly wrong and must be treated as a serious data integrity issue.

### Case 1: Same internal ID, different object meaning
This is corruption or a generation bug.

Action:
- reject mutation
- log integrity error
- mark sync as failed

### Case 2: Same provider external ID mapped to multiple internal IDs
This is import/dedupe failure.

Action:
- mark conflict
- stop automatic merge for that record set
- require deterministic repair path

### Case 3: Missing internal ID on shared object
This is invalid contract data.

Action:
- reject shared write
- generate diagnostic log
- do not guess links from title/time alone unless running a deliberate repair tool

---

## Local database IDs

Apps may still use local storage row identifiers internally.

That is allowed.

But:

- local row IDs are not shared IDs
- local row IDs must not be exposed as canonical object identity
- local row IDs must not be used for cross-app references

Canonical identity must survive storage migrations and platform differences.

---

## Offline behavior

Stable ID generation must work offline.

Both ZoesCal and ZoesTM should be able to:

- create new objects offline
- assign final canonical IDs immediately
- sync later without replacing them

This is one reason autoincrement-only database IDs are not acceptable as shared identity.

---

## Deletion behavior

Deletion does not destroy identity history immediately.

Recommended behavior:

- deleted records keep their canonical ID in tombstone form or deletion log long enough for sync correctness
- deletion sync events must reference the original internal ID
- do not recycle IDs

An old ID must never be reassigned to a new object.

---

## Non-goals

This ADR does not define:

- exact database schema
- exact sync transport
- exact tombstone retention duration
- exact choice between UUIDv7 and ULID
- exact repair tooling for corrupted identity maps

Those can be decided later as long as they follow this identity model.

---

## Alternatives considered

### Alternative A: Use external provider IDs as canonical IDs

Rejected.

Reason:
Not all objects come from providers, providers differ by type, and provider IDs do not represent app-owned identity well.

---

### Alternative B: Use database autoincrement integers

Rejected.

Reason:
They do not travel well across apps, offline creation, migrations, or multi-source sync.

---

### Alternative C: Reconstruct identity from title and time

Rejected.

Reason:
That is deduplication heuristics, not identity. It will fail on edits, collisions, and repeated tasks/events.

---

### Alternative D: Different ID schemes per app

Rejected.

Reason:
That creates translation complexity and increases risk of duplication and mapping bugs.

---

## Consequences

### Positive

- reliable sync
- safer deduplication
- correct linking between tasks, blocks, reminders, and events
- offline-safe creation
- better debugging and repairability
- cleaner external integration mapping

### Costs

- requires careful import mapping
- requires explicit provider identity storage
- requires integrity checks in sync code
- requires discipline not to leak local row IDs into shared APIs

---

## Implementation guidance

Minimum required implementation steps:

1. choose canonical ID generator format
2. add prefixed opaque IDs to all shared entities
3. store provider IDs separately in source metadata
4. make relationship fields point only to canonical IDs
5. enforce idempotent upsert-by-ID behavior
6. add integrity checks for duplicate provider mappings
7. add tombstone/deletion handling that preserves IDs

---

## Final statement

Shared objects must have one stable internal identity for life.

That identity belongs to the shared contract, not to any one UI, database row, or provider.

Everything else is metadata.
