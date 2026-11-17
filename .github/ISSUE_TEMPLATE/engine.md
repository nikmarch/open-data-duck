---
name: Engine / connector work
description: Track missing DuckDB engine, extension, or routing support
title: "Engine: "
labels: [engine]
body:
  - type: textarea
    id: need
    attributes:
      label: Need
      description: Which source family or query path needs support?
    validations:
      required: true
  - type: textarea
    id: current
    attributes:
      label: Current state
      description: Existing libraries/extensions and gaps.
    validations:
      required: true
  - type: textarea
    id: acceptance
    attributes:
      label: Acceptance criteria
      description: Testable done state.
    validations:
      required: true
