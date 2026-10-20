# Step 6: Import a bank CSV

> Milestone 2, step 2 of 3. You write the code, I review it.

## How we work on each step

```
1. PLAN      (this file)            Claude writes it
2. BUILD     you implement          one story at a time, commit per story
3. REVIEW    Claude reviews         # REVIEW comments in your files + summary
4. RESOLVE   you fix the comments
5. RE-REVIEW Claude checks again    repeat 4-5 until clean
6. DONE      Claude says "step 6 is done" -> we plan step 7
```

Rule of thumb: ask me for a hint any time, but say what you are stuck on. I will point you to the concept to look up, not hand you the code.

---

## Goal

Add a menu option **"Import bank statement"** that reads a bank CSV file and adds its spending to your expenses:

- clean the data: parse dates and amounts the way a bank writes them,
- **skip bad rows and report them** (which line, why) instead of crashing,
- raise a **custom exception** when the file cannot be read at all,
- the rest of the app keeps working as before.

Bank rows have no category. Give every imported expense `Category.OTHER` for now. Smart categorisation (regex, then an LLM) is a later step, and this import is what feeds it.

---

## Sample data (already in the repo)

You do not need a real bank file. Two synthetic files are in `samples/`:

| File | Use |
|---|---|
| `samples/bank_statement_sample.csv` | 25 data rows, written the way a bank exports: a header, a date format, quoted amounts, a running balance. It is **deliberately messy**. Part of your job is to read the file yourself (open it in a text editor, not Excel) and find out what is in it. |
| `samples/unreadable_sample.csv` | Not valid text. Used for the "cannot read the file" story. |

Rules for sample data:
- These files are synthetic and committed. Your real bank export, if you want to try one later, goes in a git-ignored place (add it to `.gitignore` **before** you copy it into the repo), never in `samples/`.
- Do not edit the sample files to make your code pass. If you want extra cases, add a new file.

---

## Target folder structure

```
expense-tracker/
├── main.py                      # now also creates the importer and hands it to the cli
├── samples/                     # synthetic CSVs (committed)
└── app/
    ├── models/                  # unchanged
    ├── storage/                 # unchanged
    ├── importers/               # NEW
    │   ├── __init__.py          # re-exports what other layers use
    │   ├── errors.py            # your custom exception for unreadable files
    │   └── csv_importer.py      # reads the CSV, returns an import result
    ├── services/                # gains a way to add many expenses at once
    └── cli/                     # gains the menu option and the report printing
```

### Who is allowed to import whom

| Layer | Job | May import | Must NOT |
|---|---|---|---|
| `importers` | Turn a file into expenses + a list of skipped rows | `models`, stdlib (`csv`, `pathlib`, `datetime`, `decimal` if you choose) | `input()` / `print()`, touch `expenses.json`, import `services` or `cli` |
| `services` | Rules | `models` (and what it already imports) | read the CSV itself |
| `cli` | Ask for the file path, print the report | `services`, `importers` (its result type and exception) | parse CSV text or do the maths |

The importer **returns** a result; it does not save anything. Saving is the service's job. That keeps it testable in step 7.

---

## User stories

Do them in this order. Commit after each story.

### Story 1: Read the file
**As a** developer, **I want** to read the CSV rows, **so that** I can work with them in code.

Look up: the `csv` module (`csv.DictReader`), `open(..., newline="")`, file encodings, context managers (`with`).

**Acceptance criteria**
- [ ] A function or class in `importers/csv_importer.py` reads `samples/bank_statement_sample.csv` and yields each row with its **line number in the file**.
- [ ] Amounts like `"2,450.00"` (a comma inside quotes) arrive as one field, not two.
- [ ] You opened the sample in a plain text editor and wrote down, in a comment at the top of the module, what kinds of rows and values you found. (You do this by reading, not by running the code.)
- [ ] `python -c "import app.importers"` works from the repo root.

### Story 2: Turn a good row into an `Expense`
**As a** user, **I want** bank rows converted into my own `Expense` type, **so that** they behave like any other expense.

Look up: `datetime.strptime` / `date.strptime` and format codes, `str.strip`, converting amount text to a number, `Decimal` vs `float` (and why money people prefer one).

**Acceptance criteria**
- [ ] A normal spending row becomes an `Expense` with the right date, a positive `amount`, the cleaned description and `Category.OTHER`.
- [ ] You decided, for **every kind of row you found in Story 1**, whether it is imported, and wrote that decision as a comment next to the code that handles it. Rows that are not spending are not imported as expenses.
- [ ] `Expense` stays as it is. If `Expense` rejects something, that rejection is a **signal** you use in Story 3, not something you work around.
- [ ] No parsing code lives outside `importers/`.

### Story 3: Skip bad rows and report them
**As a** user, **I want** the import to carry on past rows it cannot use, and tell me about them, **so that** one bad line does not stop everything and I can fix it myself.

Look up: `dataclass` for a small result type, catching a specific exception and carrying on, `list[...]` of skipped items, f-strings for messages.

**Acceptance criteria**
- [ ] The importer returns **one result object** holding: the imported expenses and the skipped rows.
- [ ] Each skipped row records the **line number**, the **original text of the row**, and a **human-readable reason** (not just "error").
- [ ] You can tell "not spending, ignored on purpose" apart from "broken, skipped". Decide how you show that, and say in one line why.
- [ ] A bad row never stops the loop and never raises out of the importer.
- [ ] Your catch blocks name specific exceptions, not bare `except:` or `except Exception:`.
- [ ] Running it on the sample file gives a count of imported, ignored and skipped rows that you can explain row by row. Write the numbers and your explanation in the commit message.

### Story 4: Unreadable files
**As a** user, **I want** a clear message when the file itself is wrong, **so that** I know it is the file and not my data.

Look up: custom exceptions (you did this in step 5), `raise ... from err`, `FileNotFoundError`, `UnicodeDecodeError`, `PermissionError`.

**Acceptance criteria**
- [ ] A custom exception in `importers/errors.py` is raised for a file that cannot be read. It has a clear name and message.
- [ ] `samples/unreadable_sample.csv` raises it.
- [ ] A path that does not exist raises it too (or you decide it deserves a different exception and say why).
- [ ] The original exception is kept as the cause.
- [ ] A file with no usable header does not crash with a raw `KeyError`. Decide what should happen and make it so.

### Story 5: Add it to the app
**As a** user, **I want** a menu option "Import bank statement", **so that** I can use the feature.

Look up: dependency injection (same as step 5), how your dispatch table in `menu.py` works.

**Acceptance criteria**
- [ ] The menu has the new option. The CLI asks for the file path and calls the importer.
- [ ] The service has one method that adds a **list** of expenses and saves **once**, not once per expense. It keeps the same promise as `add_expense` if saving fails (nothing half-added).
- [ ] After an import the user sees a short report: how many were imported, how many ignored, and the skipped rows with line number and reason.
- [ ] The unreadable-file exception is caught in the CLI and shown as a friendly message. The app does not crash and the menu continues.
- [ ] Importing the same file twice does **not** silently double your data. Decide what happens and write the decision down. (Hint style: tell me if you get stuck on how to detect it.)
- [ ] `main.py` is still only wiring.

### Story 6: Docs and clean-up
**Acceptance criteria**
- [ ] `README.md` has the new folder and the import option in the structure section, and a line on the CSV format it expects (columns, date format, sign of amounts).
- [ ] The dependency table above is respected.
- [ ] `ruff` / flake-style cleanliness is not required, but no dead code and no leftover debugging prints.

---

## Definition of done for step 6

Everything below is true and I have signed off in the review:

- [ ] All 6 stories' checkboxes are ticked.
- [ ] You ran the app yourself in a **temp folder** (never against your real `expenses.json`): import the sample, import it again, import the unreadable file, import a path that does not exist, then restart and check the data is still there.
- [ ] Your numbers from Story 3 match what the menu report shows.
- [ ] Code runs on the Python version of your venv.
- [ ] Work is committed in small commits on a branch like `step-6-csv-import`.

## Handing over for review

Tell me which stories are ready. I will review with `# REVIEW` comments in your files plus a short summary. Then you resolve and I re-review. I will say explicitly when step 6 is done.

## Preview of step 7 (not now)

Better reports: monthly summaries, top categories (`Counter`, `defaultdict`), filters by date or category, plus a few simple pytest tests. The importer returns a plain result object and does no I/O beyond reading, so it is easy to test then. Step 7 ends milestone 2 and gets the `v2` tag.
