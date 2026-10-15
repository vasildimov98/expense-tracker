# Step 5: Dataclass, Enum and a real project structure

> Milestone 2, step 1 of 4. You write the code, I review it.

## How we work on each step

```
1. PLAN      (this file)            Claude writes it
2. BUILD     you implement          one story at a time, commit per story
3. REVIEW    Claude reviews         # REVIEW comments in your files + summary
4. RESOLVE   you fix the comments
5. RE-REVIEW Claude checks again    repeat 4-5 until clean
6. DONE      Claude says "step 5 is done" -> we plan step 6
```

Rule of thumb: ask me for a hint any time, but say what you are stuck on. I will point you to the concept to look up, not hand you the code.

---

## Goal

Replace the loose `dict` expenses and the single 170-line `main.py` with:

- an `Expense` **dataclass** and a `Category` **enum**,
- small classes with one job each, in a package with a clear folder layout,
- one entry point, `python main.py`, that wires everything together.

**The app behaves the same for the user.** This step is a refactor plus typed models, not new features.

---

## Target folder structure

```
expense-tracker/
├── main.py                      # entry point: builds objects, starts the app. No logic.
├── expenses.json                # user data (git-ignored)
├── README.md
├── plans/                       # these step plans
└── app/                         # the package (all real code lives here)
    ├── __init__.py
    ├── models/
    │   ├── __init__.py          # re-exports Expense, Category
    │   ├── category.py          # Category (Enum)
    │   └── expense.py           # Expense (dataclass)
    ├── storage/
    │   ├── __init__.py          # re-exports JsonExpenseStorage
    │   └── json_storage.py      # JsonExpenseStorage: load/save to a JSON file
    ├── services/
    │   ├── __init__.py          # re-exports ExpenseService
    │   └── expense_service.py   # ExpenseService: add, delete, list, summary rules
    └── cli/
        ├── __init__.py          # re-exports ExpenseCli
        ├── prompts.py           # ask_amount, ask_category, ask_index ... (all input())
        └── menu.py              # ExpenseCli: menu loop and printing
```

Why this shape (and why `tests/` is not here yet): step 6 adds `tests/` and pytest, and step 7 adds CSV storage next to `json_storage.py`. This layout is what makes both of those easy.

### Who is allowed to import whom

```
main.py
  └─> cli      ──> services ──> models
  └─> storage  ───────────────> models
```

| Layer | Job | May import | Must NOT |
|---|---|---|---|
| `models` | Data shape only | stdlib | import anything from the project |
| `storage` | Read/write the file | `models` | call `input()` / `print()` of menus, hold business rules |
| `services` | Business rules (add, delete, totals) | `models` | call `input()`, call `print()`, touch files |
| `cli` | Talk to the user | `services`, `models` | read/write files, do the maths |
| `main.py` | Create objects and connect them | everything | contain logic |

Imports are **absolute** and run from the repo root, for example `from app.models import Expense`.

### The one start point

`main.py` does only this, in this order:

1. create the storage object (file name goes in here)
2. create the service, handing it the storage
3. create the CLI, handing it the service
4. call `cli.run()`

This is called **dependency injection** (you know it from C#). Look it up by that name. Classes receive what they need in `__init__` instead of creating it themselves.

---

## User stories

Do them in this order. You build **bottom-up** (models -> storage -> service -> cli), and `main.py` is last because it only connects the finished pieces. Until Story 7 the old `main.py` keeps running unchanged, and each new class is tried on its own (for example in a Python shell or a throwaway script).

### Story 1: Skeleton and entry point
**As a** developer, **I want** the project laid out as a package with one entry point, **so that** each part has an obvious home.

Look up: `__init__.py`, Python packages vs modules, `if __name__ == "__main__"`.

**Acceptance criteria**
- [ ] The folders and files in the tree above exist (the new files can be empty for now, except the `__init__.py` files you re-export from later).
- [ ] `python -c "import app"` runs from the repo root without an error.
- [ ] The old `main.py` is **untouched** and `python main.py` still works exactly like v1. It is your reference while you port the code; it is replaced in Story 7.

### Story 2: `Category` enum
**As a** user, **I want** categories to come from a fixed list, **so that** the same category is never spelled two ways.

Look up: `enum.Enum` (and `.value` vs `.name`).

**Acceptance criteria**
- [ ] `Category` lives in `models/category.py` and has at least: food, transport, entertainment, bills, other.
- [ ] No category is written as a bare string anywhere else in the code.
- [ ] The user picks a category by choosing from a numbered list, not by typing free text.
- [ ] You can turn a stored string back into a `Category`, and a `Category` into a string for the JSON file.

### Story 3: `Expense` dataclass
**As a** developer, **I want** an `Expense` type, **so that** I stop reading fields with `item["amount"]`.

Look up: `@dataclass`, type hints on fields.

**Acceptance criteria**
- [ ] `Expense` lives in `models/expense.py` with `category: Category`, `amount`, `description`, `date`.
- [ ] `date` is a real `datetime.date`, not a string.
- [ ] `Expense` can be converted to a plain dict for JSON and built back from one (methods on the class).
- [ ] No dict is used to represent an expense outside that conversion code.

### Story 4: JSON storage class
**As a** user, **I want** my expenses saved and loaded as before, **so that** I do not lose data.

Look up: classes and `__init__`, instance attributes, `pathlib.Path` (optional but nice).

**Acceptance criteria**
- [ ] `JsonExpenseStorage(path)` has `load() -> list[Expense]` and `save(expenses)`.
- [ ] A missing file gives an empty list.
- [ ] A corrupt file is backed up as `.bak` and gives an empty list, exactly like v1.
- [ ] Your existing `expenses.json` from v1 still loads. Decide what happens to an old entry whose category is not in the enum, and write that decision as a comment.
- [ ] The class does not know the menu or the CLI exists.

### Story 5: Expense service
**As a** developer, **I want** the rules for add, delete and totals in one class, **so that** they can be tested without a keyboard.

Look up: separation of concerns, `collections.defaultdict` or `collections.Counter` (for totals).

**Acceptance criteria**
- [ ] `ExpenseService` receives the storage in `__init__` and loads the list once at start-up.
- [ ] It has methods to add, delete (by position), list, and compute the summary (total, total per category, largest expense).
- [ ] It saves through the storage after each change.
- [ ] It never calls `input()` or `print()`.
- [ ] Deleting a position that does not exist raises a **custom exception** (you learned those), not a bare `IndexError` or a printed message.

### Story 6: CLI class
**As a** user, **I want** the same menu as before, **so that** nothing feels different.

Look up: methods vs functions, `self`, keeping a dispatch table (`dict` of choice -> method) instead of an if/elif chain.

**Acceptance criteria**
- [ ] `ExpenseCli(service)` has `run()` with the menu loop.
- [ ] Every `input()` and `print()` lives in `cli/`. Prompts that only ask-and-validate are in `prompts.py`.
- [ ] The five menu options (add, list, delete, summary, exit) work as in v1.
- [ ] The CLI catches your custom exception and shows a friendly message; it does not crash.
- [ ] Exit leaves no data unsaved.

### Story 7: Wire-up and clean-up
**As a** developer, **I want** `main.py` to be the single starting point, **so that** the pipeline is obvious.

**Acceptance criteria**
- [ ] `main.py` is about 10 lines: storage -> service -> cli -> `run()`.
- [ ] `main.py` has no business logic and no `input()` / `print()` of its own.
- [ ] `python main.py` starts the app and everything works end to end.
- [ ] The old top-level functions and the `options` dict are gone from `main.py`.
- [ ] `expenses.json` and `expenses.json.bak` are still git-ignored.
- [ ] `README.md` has a 3-line "how to run" and a one-line description of each folder.

---

## Definition of done for step 5

Everything below is true and I have signed off in the review:

- [ ] All 7 stories' checkboxes are ticked.
- [ ] You ran the app yourself and tried: add, list, delete, summary, exit, restart (data is still there), and starting with a missing and a broken `expenses.json`.
- [ ] Dependency table above is respected (I will check the imports).
- [ ] Code runs on the Python version you use for the course (`python --version` in your venv; your system `python3` is older, so do not assume the venv).
- [ ] Work is committed in small commits, one per story or so, on a branch like `step-5-structure`.

## Handing over for review

When you think a story (or all of them) is ready, tell me which stories and I will do the review: `# REVIEW` comments in your files plus a short summary of what to fix. Then you resolve, tell me, and I re-review. I will say explicitly when step 5 is done.

## Preview of step 6 (not now)

Tests with pytest for `ExpenseService` and `JsonExpenseStorage`. Story 5 is written so that it is testable without any input or files; that is the point of the split.
