from app.models import Category
from math import isfinite

class Prompts:
    def ask_choice(self):
        try:
            choice = int(input("Enter your choice: "))
            return choice
        except ValueError:
            return None

    def ask_category(self) -> Category:
        while True:
            print("Available categories:")
            for i, category in enumerate(Category, start=1):
                print(f"{i}: {category.value}")
            category_choice = input(f"Choose a number b/w 1 and {len(Category)}: ").strip()
            if category_choice.isdigit():
                category_index = int(category_choice)
                if 1 <= category_index <= len(Category):
                    return list(Category)[category_index - 1]
            print("Invalid category. Try Again :)")

    def ask_amount(self) -> float:
          while True:
            try:
                amount = float(input("How much: "))
            except ValueError:
                print("Error: amount must be a number. Try Again :)")
            else:
                if not isfinite(amount) or amount <= 0:
                    print("Amount should be a positive valid number")
                    continue
                return amount

    def ask_description(self) -> str:
        return input("Description: ").strip()

    def ask_index(self, max_index: int) -> int:
        while True:
            try:
                index = int(input(f"Which expense do you want me to delete: valid choices [1:{max_index}]: "))
                if 1 <= index <= max_index:
                    return index - 1
                else:
                    print(f"Invalid choice. Please enter a number between 1 and {max_index}.")
            except ValueError:
                print("Invalid input. Please enter a number.")