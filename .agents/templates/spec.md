---
id: S-XXX
title: <short title>
status: draft   # draft | ready | red | green | done
idea: I-XXX
capability: <capability>   # living spec this slice merges into: specs/<capability>.md
---

# Goal

<!-- One sentence: who can do what, and what value they get. No "and". -->

# Scope

## In

-

## Out

<!-- Never empty. What a reader might expect here but is deliberately excluded. -->

-

# Boundaries

<!-- Everything this slice touches, and nothing else. -->

- **Input:** <!-- endpoint / event / UI action + data shape -->
- **Output:** <!-- response / side effect / persisted state -->
- **Touches:** <!-- modules, tables, services -->
- **Contracts:** <!-- interfaces with other slices or systems, and who owns each -->

# Acceptance criteria

<!-- 1–6 criteria. Each one observable from the boundary, not from internals.
     IDs are stable: never renumber; strike out removed ones. -->

- **AC-1:** Given <context>, when <action>, then <observable result>.
- **AC-2:** Given <context>, when <action>, then <observable result>.

# Constraints

<!-- Only the ones that apply: performance, security, compatibility, limits. Delete if none. -->

-

# Open questions

<!-- Must be empty to move to `ready`. -->

-
