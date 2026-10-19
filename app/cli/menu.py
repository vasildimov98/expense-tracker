from app.services import ExpenseService, ExpenseNotFoundError
from app.models import InvalidExpenseError
from app.storage import CorruptStorageError
from app.cli.prompts import Prompts

class ExpenseCli:
    def __init__(self, expense_service: ExpenseService, prompts: Prompts):
        self.expense_service = expense_service
        self.prompts = prompts
        self._options = {
            1: "Add Expense",
            2: "List Expenses",
            3: "Delete Expense",
            4: "Show Summary",
            5: "Exit"
        }

    def run(self):
        try:
            self.expense_service.load_expenses()
        except CorruptStorageError as e:
            print(f"Warning: could not load expenses due to corrupt storage: {e}")
        choices_actions_map = {
                1: self.add_expense,
                2: self.list_expenses,
                3: self.delete_expense,
                4: self.show_summary,
            }
        while True:
            self._show_menu()
            choice = self.prompts.ask_choice()

            if choice == 5:
                break
            action = choices_actions_map.get(choice)

            if action:
                action()
            else:
                self._show_invalid_choice()

    def add_expense(self):
        category = self.prompts.ask_category()
        amount = self.prompts.ask_amount()
        description = self.prompts.ask_description()
        try:
            self.expense_service.add_expense(category, amount, description)
        except InvalidExpenseError as e:
            print(f"Error adding expense: {e}")

    def list_expenses(self):
        expenses = self.expense_service.get_expenses()
        if not expenses:
            print("No expenses added yet. Spend some money and come back :P")
            return
        
        for number, expense in enumerate(expenses, start=1):
            description = "Not Provided"
            if expense.description != "":
                description = expense.description

            print(f"{number}: Category {expense.category.value}, Amount: {expense.amount:.2f} Description: {description}, Date: {expense.date}")

    def delete_expense(self):
        if not self.expense_service.get_expenses():
            print("Nothing to delete here :O")
            return

        self.list_expenses()
        index = self.prompts.ask_index(len(self.expense_service.get_expenses()))
        try:
            self.expense_service.delete_expense(index)
        except ExpenseNotFoundError as e:
            print(f"Error deleting expense: {e}")

    def show_summary(self):
        summary = self.expense_service.compute_summary()
        print(f"Total: {summary.total:.2f}")
        for category, total in summary.total_per_category.items():
            print(f"{category.value}: {total:.2f}")
        if summary.largest_expense:
            le = summary.largest_expense
            print(f"Largest Expense: {le.category.value} - {le.amount:.2f} - {le.description}")

    def _show_menu(self):
        print(f"Make your choice: {', '.join(str(key) for key in self._options)}")
        for key, value in self._options.items():
            print(f"{key}: {value}")
        print()

    def _show_invalid_choice(self):
        print("Invalid choice, please try again.")
