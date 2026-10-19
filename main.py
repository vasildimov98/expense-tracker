from app.cli.menu import ExpenseCli
from app.cli.prompts import Prompts
from app.services import ExpenseService
from app.storage import JsonExpenseStorage

def main():
    expense_service = ExpenseService(expense_storage=JsonExpenseStorage("expenses.json"))
    prompts = Prompts()
    cli = ExpenseCli(expense_service=expense_service, prompts=prompts)
    cli.run()

if __name__ == "__main__":
    main()