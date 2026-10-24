---
id: S-XXX
title: <short title>
status: draft               # draft | ready | red | green | done (set by the CLI)
track: fix                  # fix slice: at most 2 criteria, no plan, no new ADR
idea: I-XXX                 # source idea; remove for a standalone fix
capability: <capability>    # living spec this slice merges into: specs/<capability>.md
change: fixed               # fixed | security
breaking: false             # true only if the fix stops a contract working for its consumers
adrs: []                    # accepted decisions this fix follows, e.g. [ADR-003]
---

# Goal

<!-- One sentence: who gets the right behavior, and what it is. -->

# Bug

- **Actual:** <!-- what happens today, from the boundary -->
- **Expected:** <!-- what should happen, and the source: a living spec criterion, a contract or the user -->

# Scope

## In

- The behavior described in Expected

## Out

- Other defects found on the way: each becomes its own slice

# Boundaries

<!-- Write "none" where nothing applies. -->

- **Input:** <!-- endpoint / event / UI action that shows the bug -->
- **Output:** <!-- the result that is wrong today -->
- **Touches:** <!-- modules, tables, services -->
- **Contracts:** <!-- interfaces involved, or none -->

# Acceptance criteria

<!-- 1–2 criteria that reproduce the bug: they fail today and pass once fixed. -->

- **AC-1:** Given <context>, when <action>, then <observable result>.

# Open questions

<!-- Must be empty to move to `ready`. -->

-
