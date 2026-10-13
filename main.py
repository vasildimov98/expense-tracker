from datetime import date
from math import isfinite
import json
import os

options = {
    1: "Add Expense",
    2: "List Expenses",
    3: "Delete Expense",
    4: "Show Summary",
    5: "Exit"
}

expenses_file_name = "expenses.json"

def show_menu():
    print(f"Make your choice: {', '.join(str(key) for key in options)}")
    for key, value in options.items():
        print(f"{key}: {value}")
    print()

def ask_amount():
    while True:
        try:
            amount = float(input("Amount: "))
        except ValueError:
            print("Error: amount must be a number. Try Again :)")
        else:
            if not isfinite(amount) or amount <= 0:
                print("Amount should be a positive valid number")
                continue
            return amount
            

def ask_index(expenses_len):
    while True:
        try:
            index = int(input(f"Which expense do you want me to delete: valid choices [1:{expenses_len}]: "))
        except ValueError:
            print("Error: index must be a valid number. Try Again :)")
        else: 
            return index

def ask_category():
    while True:
        category = input("Category: ").strip()
        if category != "":
            return category
        print("Category is required. Try Again :)")

def add_expense(expenses: list):
    category = ask_category()
    amount = ask_amount()
    description = input("Description: ").strip()

    today = date.today().isoformat()

    expense = {"category": category, "amount": amount, "description": description, "date": today}
    expenses.append(expense)

    print("Expense Added")

def list_expenses(expenses: list):
    if len(expenses) == 0:
        print("No expenses added yet. Spend some money and come back :P")
        print()
        return

    for number, item in enumerate(expenses, start = 1):
        description = "Not Provided"
        if item["description"]:
            description = item["description"]

        print(f"{number}: Category {item['category']}, Amount: {item['amount']:.2f} Description: {description}, Date: {item['date']}")

    print()

def ask_expense_index(expenses_len: int): 
    while True:
        index = ask_index(expenses_len)

        if index < 1 or index > expenses_len:
            print(f"Valid digits are [1:{expenses_len}]")
            continue

        return index - 1


def delete_expense(expenses: list):  
    expenses_len = len(expenses)

    if expenses_len == 0:
        print("Nothing to delete here :O")
        return
    
    list_expenses(expenses)

    index = ask_expense_index(expenses_len)

    expense = expenses.pop(index)
    print(f"Successfully deleted {expense['category']}")
    print()

def show_summary(expenses):
    if len(expenses) == 0:
        print("Nothing to show yet")
        return
    
    total = 0 
    total_by_category = {} 
    for expense in expenses:
        curr_amount = expense["amount"]
            
        total += curr_amount

        category = expense["category"]
        total_by_category[category] = total_by_category.get(category, 0) + curr_amount

    print(f"Total expenses: {total:.2f}")

    for category, amount in total_by_category.items():
        print(f"  {category}: {amount:.2f}")

    print(f"Largest expense: {max([ex['amount'] for ex in expenses]):.2f}")

def save_expenses(expenses: list, filename: str):
    with open(filename, "w") as f:
        json.dump(expenses, f, indent = 4)

def load_expenses(filename: str):
    try:
        with open(filename, "r") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("expected a list of expenses")
        return data
    except FileNotFoundError:
        # First run: there is nothing saved yet, which is normal, not an error.
        return []
    except ValueError:
        # json.JSONDecodeError is a subclass of ValueError, so this catches both unreadable JSON
        # and the wrong-shape case raised above. Keep the broken file as a backup instead of
        # letting the next save silently overwrite it.
        backup = filename + ".bak"
        os.replace(filename, backup)
        print(f"Could not read {filename}. Saved a copy as {backup} and starting with an empty list.")
        return []


def main():
    expenses = load_expenses(expenses_file_name)
    while True:
        show_menu()
        choice = input("Choice: ").strip()
        if choice == "1": # add 
            add_expense(expenses)
            save_expenses(expenses, expenses_file_name)
        elif choice == "2": # list
            list_expenses(expenses)
        elif choice == "3": # delete
            delete_expense(expenses)
            save_expenses(expenses, expenses_file_name)
        elif choice == "4": # show
            show_summary(expenses)
        elif choice == "5": # exit
            save_expenses(expenses, expenses_file_name)
            print("Have a nice day! Goodbye :)") 
            break
        else:
            print(f"{choice} is invalid. Try again :)")

if __name__ == "__main__":
    main()

