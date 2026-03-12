# ADR 0004: ZoesCal Skin Token Architecture

## Status

Accepted

## Date

2026-03-10

## Decision

ZoesCal will use a token-based skin architecture for all visual theming.

Skins must affect presentation only.
They must not change application behavior, sync logic, permissions, editability, keyboard semantics, or feature availability.

All built-in and user-created skins must theme the UI through semantic design tokens rather than component-specific one-off overrides.

This architecture will support:

- 9 built-in skins
- user-created skins through CSS/token editing
- future skin expansion without rewriting components
- consistent theming across web, desktop, and mobile-capable surfaces where applicable

---

## Why this exists

ZoesCal is intended to compete partly on visual quality and flexibility.

That means the UI needs:

- strong aesthetic variety
- maintainable theme switching
- safe customization
- accessible defaults
- a structure that does not turn into styling chaos

Without a token architecture, theming tends to become:

- hardcoded colors inside components
- inconsistent spacing and radii
- duplicated overrides
- skin-specific logic branches
- visual regressions when new features ship

Theming must scale with the product, not fight it.

---

## Core principle

Components must consume semantic tokens.

Components must not know which skin is active.

A skin defines values.
A component defines structure and behavior.
The token layer connects them.

---

## What a skin is

A skin is a named presentation preset that supplies token values for the ZoesCal interface.

A skin may define:

- colors
- typography choices
- radii
- border treatment
- shadow intensity
- spacing density within allowed ranges
- motion feel
- surface contrast
- object color mapping

A skin must not define:

- feature toggles
- drag/drop rules
- scheduling behavior
- sync state logic
- source-of-truth rules
- keyboard shortcut behavior
- permissions
- different business logic paths

---

## Architecture layers

## 1. Semantic token layer

This is the primary contract between skins and components.

Tokens must be named by meaning, not by raw appearance.

Good examples:

- `--bg-app`
- `--bg-panel`
- `--bg-panel-elevated`
- `--bg-hover`
- `--bg-selected`
- `--text-primary`
- `--text-secondary`
- `--text-muted`
- `--border-subtle`
- `--accent-primary`
- `--accent-secondary`
- `--color-success`
- `--color-warn`
- `--color-danger`
- `--timeline-now`
- `--calendar-grid-line`
- `--day-today-ring`
- `--event-default`
- `--task-default`
- `--reminder-default`
- `--shadow-soft`
- `--radius-sm`
- `--radius-md`
- `--radius-lg`
- `--motion-fast`
- `--motion-normal`

Bad examples:

- `--blue-500`
- `--sidebar-dark-gray`
- `--red-warning-card-border-final`
- `--month-view-special-hover`

Those names either encode implementation detail or lock the system to one presentation assumption.

---

## 2. Component consumption layer

Components may only reference semantic tokens or a small controlled alias layer derived from them.

Examples of themed components:

- app shell
- sidebar
- day/week/month calendar surfaces
- time grid
- day cells
- event cards
- task blocks
- reminder chips
- dialogs
- popovers
- command surfaces
- list rows
- focus states
- empty states

Components must not hardcode skin-specific colors or radii except for emergency debug-only development cases that are removed before release.

---

## 3. Skin definition layer

Each skin supplies a full or near-full token set.

A skin may be implemented as:

- a CSS file
- a theme object compiled to CSS variables
- a platform theme manifest that resolves to the same semantic token contract

The important rule is not file format.
The important rule is that all skins resolve to the same semantic token surface.

---

## 4. Optional alias layer

A small alias layer may exist to map semantic tokens into component-local names for readability.

Example:

- `--calendar-surface-bg` may alias to `--bg-panel`
- `--event-card-bg` may alias to `--event-default`

This is allowed only when it improves clarity.
It must not become a second uncontrolled token system.

---

## Required token groups

Every supported skin must provide values for the following groups.

### Surface tokens

Used for layout surfaces and containment.

Minimum examples:

- app background
- primary panel
- secondary panel
- elevated panel
- hover surface
- selected surface
- overlay/scrim surface

---

### Text tokens

Used for readable content hierarchy.

Minimum examples:

- primary text
- secondary text
- muted text
- inverted text
- link or accent text
- disabled text

---

### Border and separator tokens

Used for visual structure.

Minimum examples:

- subtle border
- strong border
- divider line
- focus ring

---

### Accent and status tokens

Used for actions and state communication.

Minimum examples:

- primary accent
- secondary accent
- success
- warning
- danger
- info

---

### Calendar-specific tokens

Used for planning surfaces.

Minimum examples:

- calendar grid line
- current time marker
- today highlight
- selected range
- day header emphasis
- busy block hint
- free slot hint

---

### Object tokens

Used for visible object categories.

Minimum examples:

- event default
- task default
- reminder default
- completed object
- blocked/conflict state
- read-only object state

---

### Shape tokens

Used for consistent physical feel.

Minimum examples:

- small radius
- medium radius
- large radius
- panel radius
- chip radius

---

### Shadow tokens

Used for depth hierarchy.

Minimum examples:

- soft shadow
- elevated shadow
- floating shadow

---

### Motion tokens

Used for interaction feel.

Minimum examples:

- fast duration
- normal duration
- slow duration
- standard easing
- emphasized easing

---

### Density and spacing tokens

Used carefully for layout rhythm.

Minimum examples:

- compact spacing
- normal spacing
- roomy spacing
- control height tiers

These should remain within safe ranges so skins do not break layout integrity.

---

## Built-in skin strategy

ZoesCal will ship with 9 built-in skins.

These should feel meaningfully different rather than being tiny recolors.

Example directions:

- clean light
- clean dark
- soft pastel
- high contrast
- midnight neon
- paper minimal
- warm analog
- glassy modern
- muted professional

These are preset directions, not architectural branches.

The codebase must not contain logic like:

- `if skin == neon then use different layout`
- `if skin == paper then disable shadows in component code`

All such differences must flow through tokens.

---

## User-created skin support

Advanced users should be able to create additional skins by editing CSS or a supported token manifest.

Minimum user flow:

1. copy an existing skin
2. edit token values
3. register the skin in a manifest or config
4. load it without component changes

This is a product feature, not just a developer convenience.

That means the architecture must be understandable enough that a power user can extend it without reverse-engineering the whole app.

---

## Registration model

Each skin should be registered with lightweight metadata.

Suggested metadata:

- skin ID
- display name
- author
- version
- base compatibility version
- dark/light/general category
- accessibility notes if relevant
- file path or manifest entry

The registration layer is for discovery and compatibility, not for behavior branching.

---

## Accessibility requirements

All built-in skins must satisfy baseline accessibility requirements.

Minimum expectations:

- readable text contrast
- visible focus states
- distinguishable task/event/reminder objects
- visible current-time marker
- readable disabled and muted states
- sufficient selected-state visibility
- usable hover and active states where relevant

A skin that looks good but obscures planning state is a broken skin.

Accessibility is not optional cosmetic polish.
It is part of the theme contract.

---

## State styling rules

Interaction and object states must also be token-driven.

States include:

- default
- hover
- active
- selected
- focused
- disabled
- read-only
- completed
- overdue
- conflict
- dragging
- drop-target

These states may use tokens or derived variables, but must still obey the same semantic system.

Do not let states become hardcoded exceptions scattered through components.

---

## Platform consistency

ZoesCal targets multiple surfaces.

The skin system should keep the same semantic model across:

- web
- desktop
- future mobile-capable UI layers

Exact rendering may differ slightly by platform toolkit, but semantic token meaning must remain stable.

Example:
`--timeline-now` should mean the same planning concept everywhere even if rendering details differ.

---

## Performance expectations

Theme switching should be lightweight.

Preferred behavior:

- switch token sets without rerendering large logic trees
- avoid recalculating business logic on theme changes
- avoid per-component runtime style generation when a variable-driven approach is enough

Skins are presentation changes and should behave like presentation changes.

---

## Versioning and compatibility

Skin compatibility should be managed explicitly.

When token requirements change:

- add new tokens with sensible fallbacks where possible
- version the skin contract
- document required tokens
- avoid silently breaking older custom skins without warning

A custom skin ecosystem is only viable if contract evolution is predictable.

---

## Fallback behavior

If a skin is incomplete or invalid:

- missing tokens should fall back to base tokens where safe
- invalid values should not crash the app
- the app should log helpful diagnostics in development
- production should degrade gracefully to safe defaults where possible

However, fallback should not hide severe incompatibility forever.
Broken skins should be detectable.

---

## Testing expectations

The theme system should be tested at multiple levels.

Minimum useful tests:

- token presence validation
- skin registration validation
- screenshot or visual regression checks for built-in skins
- accessibility checks for contrast and focus visibility
- state rendering checks for events, tasks, reminders, and conflict markers

Visual flexibility without validation will drift into inconsistency.

---

## File structure direction

A reasonable structure is:

- `skins/base-tokens.css`
- `skins/manifest.json`
- `skins/skin-clean-light.css`
- `skins/skin-clean-dark.css`
- `skins/skin-soft-pastel.css`
- `skins/skin-high-contrast.css`
- `skins/skin-midnight-neon.css`
- `skins/skin-paper-minimal.css`
- `skins/skin-warm-analog.css`
- `skins/skin-glassy-modern.css`
- `skins/skin-muted-professional.css`
- `skins/README.md`

Exact filenames may change, but separation of base, manifest, and skin definitions should remain.

---

## Non-goals

This ADR does not define:

- the exact frontend framework styling solution
- the exact mobile rendering implementation
- the final font licensing choices
- the final built-in skin names
- advanced community packaging/distribution for skins
- per-user cloud syncing of skins

Those can be decided later as long as they preserve this architecture.

---

## Alternatives considered

### Alternative A: Hardcode styles in components and add overrides later

Rejected.

Reason:
This is the fastest way to produce an unmaintainable theme system.

---

### Alternative B: Allow each skin to ship component-specific CSS freely

Rejected.

Reason:
That creates drift, fragile overrides, and hidden behavior coupling.

---

### Alternative C: Use only one light and one dark theme

Rejected.

Reason:
The product direction explicitly values broader visual customization.

---

### Alternative D: Let skins modify layout and behavior for stronger personality

Rejected.

Reason:
That would make theming dangerous, harder to test, and likely to interfere with usability and sync expectations.

---

## Consequences

### Positive

- cleaner component architecture
- easy skin swapping
- safer user-extensible theming
- better long-term maintainability
- clearer accessibility enforcement
- consistent visual language across surfaces

### Costs

- more upfront token design work
- need for discipline in component styling
- need for validation and regression testing
- need for versioning as the token contract evolves

---

## Implementation guidance

Minimum implementation steps:

1. define the semantic token contract
2. create base tokens and safe defaults
3. refactor components to consume tokens only
4. ship 2 to 3 skins first to validate architecture
5. expand to the full built-in 9 after the system holds up
6. add manifest-based registration
7. add validation and visual regression checks
8. document custom skin authoring clearly

---

## Final statement

ZoesCal skins must theme the product without mutating the product.

Meaning lives in components and contracts.
Presentation lives in tokens.

That boundary is what makes 9 built-in skins and user-created skins sustainable.
