from datetime import date

options = {
    1: "Add Expense",
    2: "List Expenses",
    3: "Delete Expense",
    4: "Show Balance",
    5: "Exit"
}

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
            return amount

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

def show_coming_soon_label():  
    print("coming soon")

def main():
    expenses = []
    while True:
        show_menu()
        choice = input("Choice: ").strip()
        if choice == "1": # add 
            add_expense(expenses)
        elif choice == "2": # list
            list_expenses(expenses)
        elif choice == "3": # delete
            show_coming_soon_label()
        elif choice == "4": # show
            show_coming_soon_label()
        elif choice == "5": # exit
            print("Have a nice day! Goodbye :)") 
            break
        else:
            print(f"{choice} is invalid. Try again :)")

if __name__ == "__main__":
    main()

