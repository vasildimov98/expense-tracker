from dataclasses import dataclass, field
import datetime as dt
import math
from  .category import Category

class InvalidExpenseError(ValueError):
    pass

@dataclass(frozen=True)
class Expense:
    category: Category
    amount: float
    description: str
    date: dt.date = field(default_factory=dt.date.today)

    def __post_init__(self):
        if self.amount is None:
            raise InvalidExpenseError("Amount must be provided")
        if not isinstance(self.amount, (int, float)):
            raise InvalidExpenseError("Amount must be a number")
        if math.isnan(self.amount) or math.isinf(self.amount):
            raise InvalidExpenseError("Amount must be a finite number")
        if self.amount <= 0:
            raise InvalidExpenseError("Amount must be greater than zero")
        if not isinstance(self.category, Category):
            raise InvalidExpenseError("Category must be an instance of Category")
        if not isinstance(self.description, str):
            raise InvalidExpenseError("Description must be a string")
        if not isinstance(self.date, dt.date):
            raise InvalidExpenseError("Date must be an instance of datetime.date")

    def to_dict(self) -> dict:
        return {
            "category": self.category.value,
            "amount": self.amount,
            "description": self.description,
            "date": self.date.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Expense":
        return cls(
            category=Category(data["category"]),
            amount=data["amount"],
            description=data["description"],
            date=dt.date.fromisoformat(data["date"])
        )