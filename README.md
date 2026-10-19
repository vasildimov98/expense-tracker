# Expense Tracker

A command-line expense tracker written as a **study project** to learn Python (coming from C#). It grows step by step: dicts and JSON first, then dataclasses, enums, tests, and more. It is not meant for production use.

You can add, list and delete expenses, see a summary by category, and your data is saved to `expenses.json` between runs.

## How to run

```bash
python3 -m venv .venv && source .venv/bin/activate   # once
python main.py
```

Requires Python 3.10 or newer. There are no third-party dependencies.

## Project structure

```
main.py             Entry point. Creates the objects and starts the app. No logic.
plans/              Step-by-step plans (user stories and acceptance criteria).
app/
  models/           The data: Expense (dataclass) and Category (enum), with validation.
  storage/          Reads and writes expenses.json. Backs up a corrupt file.
  services/         The rules: add, delete, list, summary. No input or printing.
  cli/              Everything the user sees and types: the menu and the prompts.
```

Each layer only depends on the ones below it:

```
main.py -> cli -> services -> models
           main.py -> storage -> models
```

## Data

Expenses are stored in `expenses.json` in the folder you run the program from. It is git-ignored, because it is personal data. If the file cannot be read, it is moved to `expenses.bak` and the app starts with an empty list.
