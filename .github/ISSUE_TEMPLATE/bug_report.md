---
name: 🐛 Bug Report
about: Create a report to help us improve the project.
title: "Bug: [A brief, descriptive title]"
labels: 'bug'
---

body:
  - type: markdown
    attributes:
      value: |
        Thank you for reporting a bug! Please fill out the sections below to help us resolve the issue as quickly as possible.

  - type: textarea
    id: bug-description
    attributes:
      label: Describe the bug
      description: A clear and concise description of what the bug is.
    validations:
      required: true

  - type: textarea
    id: to-reproduce
    attributes:
      label: To Reproduce
      description: Steps to reliably reproduce the behavior.
      placeholder: |
        1. Go to '...'
        2. Click on '....'
        3. Scroll down to '....'
        4. See error
    validations:
      required: true

  - type: textarea
    id: expected-behavior
    attributes:
      label: Expected behavior
      description: A clear and concise description of what you expected to happen.
    validations:
      required: true

  - type: textarea
    id: desktop-environment
    attributes:
      label: Your Environment
      description: Please provide details about the environment where you encountered the bug.
      placeholder: |
        - OS: [e.g. Ubuntu 22.04, Windows 11]
        - Browser: [e.g. Chrome, Firefox]
        - PiSelfhosting Version: [e.g. 0.1.0]
    validations:
      required: true

  - type: textarea
    id: additional-context
    attributes:
      label: Additional context
      description: Add any other context, logs, or screenshots about the problem here.
