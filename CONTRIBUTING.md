<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*

- [Contributing to Money Manager](#contributing-to-money-manager)
  - [Getting Started](#getting-started)
    - [1. Forking and Braching](#1-forking-and-braching)
    - [2. Setup Environment](#2-setup-environment)
    - [3. Make Changes](#3-make-changes)
    - [4. Ensure tests are passing](#4-ensure-tests-are-passing)
    - [5. Commit Changes](#5-commit-changes)
    - [6. Open a Pull Request](#6-open-a-pull-request)
  - [Code of Conduct](#code-of-conduct)
  - [Guidelines](#guidelines)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# Contributing to Money Manager

Thank you for considering contributing to **MoneyManager**! We welcome all types of contributions, whether you're fixing a bug, adding a feature, improving documentation, or suggesting an idea.

## Getting Started

To get started with contributing to this project, please follow these guidelines.

### 1. Forking and Braching

Fork this repository to your GitHub personal/org account. Clone the forked repository to your local machine and create a new branch for your feature or bug fix.

### 2. Setup Environment

See [INSTALL.md](INSTALL.md) for instructions on setting up the development environment.

### 3. Make Changes

Make your changes to the codebase. Ensure you write unit tests if applicable.

### 4. Ensure tests are passing

Before committing your changes, ensure that all tests are passing. Run the following command to execute all tests:

```bash
uv run pytest
```

### 5. Commit Changes

Please pass pre-commit checks before committing your changes. Run the following command to check:

```bash
pre-commit run --all-files
```

If you have pre-commit installed, it will check automatically before you commit. Commit your changes with a descriptive commit message.

### 6. Open a Pull Request

Push your changes to your forked repository. Once you've pushed your changes, open a pull request to the main branch.

## Code of Conduct

We expect all contributors to follow our [Code of Conduct](CODE_OF_CONDUCT.md). Please respect others' work and efforts, and let's collaborate effectively to improve **MoneyManager** together.

## Guidelines

- Write clear, concise commit messages.
- Test your changes thoroughly.
- Include tests for any new functionality.
- If you have any questions, please open an issue or contact the maintainers.
