from pathlib import Path
from app.models import Expense
import json
from .errors import CorruptStorageError

# This class provides JSON-based storage for Expense objects.
# If the storage file is found to be corrupt (invalid JSON or unexpected structure, wrong category),
# it creates a backup and raises CorruptStorageError.
class JsonExpenseStorage:
    def __init__(self, path):
        self._path = Path(path)

    def load(self) -> list["Expense"]:
        if not self._path.exists():
            return []
        try:
            data = json.loads(self._path.read_text())
            if not isinstance(data, list):
                raise ValueError("expected a list of expenses")
            return [Expense.from_dict(item) for item in data]
        except (ValueError, KeyError, TypeError) as err:
            self.backup()
            raise CorruptStorageError(f"Storage file is corrupt: backup created at {self._path.with_suffix('.bak')}") from err

    def save(self, expenses: "list[Expense]"):
        self._path.write_text(json.dumps([expense.to_dict() for expense in expenses]))

    def backup(self):
        self._path.replace(self._path.with_suffix('.bak'))
