from dataclasses import dataclass, field
from collections import defaultdict
from app.storage import JsonExpenseStorage
from app.models import Expense, Category

class ExpenseNotFoundError(Exception):
    pass

@dataclass
class Summary:
    total: float
    total_per_category: dict
    largest_expense: Expense | None

@dataclass
class ExpenseService:
    expense_storage: JsonExpenseStorage
    _expenses: list[Expense] = field(init=False)

    def __post_init__(self):
        self._expenses = self.expense_storage.load()

    def add_expense(self, category: Category, amount: float, description: str):
        expense = Expense(category, amount, description)
        self._expenses.append(expense)
        try:
            self.expense_storage.save(self._expenses)
        except Exception:
            self._expenses.pop()  # rollback in-memory change if save fails
            raise

    def get_expenses(self) -> list[Expense]:
        return self._expenses.copy()

    def compute_summary(self) -> Summary:
        total = sum(expense.amount for expense in self._expenses)
        total_per_category = defaultdict(list)
        largest_expense = None
        for expense in self._expenses:
            total_per_category[expense.category].append(expense.amount)
            if largest_expense is None or expense.amount > largest_expense.amount:
                largest_expense = expense
        return Summary(
            total=total,
            total_per_category=dict({k: sum(v) for k, v in total_per_category.items()}),
            largest_expense=largest_expense
        )
    
    # Note: The delete_expense method expects a 0-based position as input
    def delete_expense(self, position: int):
        if position < 0 or position >= len(self._expenses):
            raise ExpenseNotFoundError("Expense at the given position does not exist")
        expense = self._expenses.pop(position)
        try:
            self.expense_storage.save(self._expenses)
        except Exception:
            self._expenses.insert(position, expense)  # rollback in-memory change if save fails
            raise