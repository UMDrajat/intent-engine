name: Pull Request
description: Create a pull request to contribute to Intent Engine
title: "<type>(<scope>): <brief description>"
labels: []
body:
  - type: markdown
    attributes:
      value: |
        Thank you for contributing to Intent Engine! 
        
        Please fill out this template to help us review your contribution.
        
        **Quick Checklist:**
        - [ ] Code follows project guidelines (Ruff)
        - [ ] Tests added/updated and passing
        - [ ] Documentation updated (if needed)
        - [ ] Commits follow Conventional Commits

  - type: textarea
    id: description
    attributes:
      label: Description
      description: Briefly describe your changes (1-2 sentences)
      placeholder: |
        This PR fixes issue #123 by...
        This PR adds support for...
    validations:
      required: true

  - type: dropdown
    id: type
    attributes:
      label: Type of Change
      description: What type of change is this?
      options:
        - Bug fix (non-breaking change that fixes an issue)
        - New feature (non-breaking change that adds functionality)
        - Breaking change (fix or feature that would cause existing functionality to change)
        - Documentation update
        - Performance improvement
        - Refactoring (no functional change)
        - Test addition/update
        - Maintenance (dependencies, CI/CD, etc.)
    validations:
      required: true

  - type: input
    id: issues
    attributes:
      label: Related Issues
      description: Link any related issues (e.g., "Closes #123, Fixes #456")
      placeholder: Closes #

  - type: textarea
    id: testing
    attributes:
      label: Testing Done
      description: Describe the testing you performed
      placeholder: |
        - Added unit tests in tests/test_module.py
        - Ran integration tests: pytest tests/integration/
        - Manual testing: [describe steps]
        - Load testing: [if performance-impacting]
    validations:
      required: true

  - type: checkboxes
    id: checklist
    attributes:
      label: Checklist
      description: Please confirm these items before submitting
      options:
        - label: Code follows project guidelines (`make lint` passes)
        - label: Self-review completed
        - label: Tests pass locally (`make test`)
        - label: Documentation updated (if needed)
        - label: No new warnings or errors
        - label: Coverage maintained (>80%)
        - label: Commits follow Conventional Commits
    validations:
      required: true

  - type: textarea
    id: screenshots
    attributes:
      label: Screenshots (if applicable)
      description: Add screenshots of UI changes or example API responses
      placeholder: Drag and drop screenshots here

  - type: textarea
    id: deployment
    attributes:
      label: Deployment Notes
      description: Any special deployment considerations, migrations, or configuration changes
      placeholder: |
        - Database migration required: [yes/no]
        - Environment variables to add: [...]
        - Breaking changes for existing deployments: [...]

  - type: markdown
    attributes:
      value: |
        ---
        
        **Need help?** Check out our [Contributing Guide](CONTRIBUTING.md) or reach out at likhith.anony45@gmail.com
        
        **By submitting this PR, you agree** that your contributions will be licensed under the [Intent Engine Community License (IECL) v1.0](LICENSE).
