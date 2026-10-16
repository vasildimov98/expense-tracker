from dataclasses import dataclass
import datetime as dt
from  .category import Category

@dataclass
class Expense:
    category: Category
    amount: float
    description: str
    date: dt.date

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