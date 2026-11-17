---
name: Source candidate
description: Propose an authoritative public data source for the registry
title: "Add source: "
labels: [source-candidate]
body:
  - type: textarea
    id: source
    attributes:
      label: Source
      description: Publisher, homepage, license/terms, attribution, and source type.
    validations:
      required: true
  - type: textarea
    id: duckdb
    attributes:
      label: DuckDB path
      description: Existing extension/table function, example query, and validation query.
    validations:
      required: true
  - type: textarea
    id: review
    attributes:
      label: Review notes
      description: Why this is authoritative, plus risks or blockers.
    validations:
      required: true
