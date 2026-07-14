---
name: ✨ Feature Request
about: Suggest an idea or new functionality for PiSelfhosting.
title: "Feature: [A brief, descriptive title]"
labels: 'enhancement'
---

body:
  - type: markdown
    attributes:
      value: |
        Thank you for taking the time to suggest a new feature! Please provide as much detail as possible.

  - type: textarea
    id: related-problem
    attributes:
      label: Is your feature request related to a problem?
      description: A clear and concise description of what the problem is. Ex. I'm always frustrated when [...]
      placeholder: "I'm always frustrated when..."
    validations:
      required: true

  - type: textarea
    id: solution
    attributes:
      label: Describe the solution you'd like
      description: A clear and concise description of what you want to happen.
    validations:
      required: true

  - type: textarea
    id: alternatives
    attributes:
      label: Describe alternatives you've considered
      description: A clear and concise description of any alternative solutions or features you've considered.

  - type: textarea
    id: additional-context
    attributes:
      label: Additional context
      description: Add any other context or screenshots about the feature request here.
