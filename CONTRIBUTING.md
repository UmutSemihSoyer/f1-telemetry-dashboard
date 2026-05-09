# Contributing to F1 2022 Pit Wall Pro

First off, thanks for taking the time to contribute! 🎉

The following is a set of guidelines for contributing to F1 2022 Pit Wall Pro. These are mostly guidelines, not rules. Use your best judgment, and feel free to propose changes to this document in a pull request.

## How Can I Contribute?

### Reporting Bugs
* **Check the Issues:** Search the issue tracker to see if the bug has already been reported.
* **Use the Template:** If it hasn't, open a new issue using the **Bug Report** template.
* **Be Specific:** Include your OS, Python version, and steps to reproduce the issue.

### Suggesting Enhancements
* **Check the Roadmap:** See if your idea is already planned.
* **Use the Template:** Open a new issue using the **Feature Request** template.

### Pull Requests
1. **Fork the repo** and create your branch from `main`.
2. **Follow PEP8:** We use `black` for formatting.
3. **Add Type Hints:** All new functions must have type hints.
4. **Update Documentation:** If you add a new feature, update the README or docstrings.
5. **Add Tests:** Ensure your code is covered by a test in the `tests/` directory.

## Technical Standards
* All core logic should reside in `core/`.
* I/O and side effects should be isolated in `services/`.
* Shared state must be managed thread-safely via `shared_state.py`.

## Style Guide
* We use **Google Style Docstrings**.
* Indentation: 4 spaces.
* Max line length: 100 characters.

Thank you for making this project better! 🏎️💨
