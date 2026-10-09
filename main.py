from datetime import date

def show_menu():
    print("Make your choice: [1, 2, 3, 4]")
    print("1. Add Expense") 
    print("2. Delete Expense")
    print("3. Show Balance")
    print("4. Exit")
    print()


def add_expense(expenses: list):
    category = input("Category: ")
    try:
        amount = float(input("Amount: "))
    except ValueError:
        print("Error: amount must be a number")
        return
    description = input("Description: ")

    today = date.today().isoformat()

    expense = {"category": category, "amount": amount, "description": description, "date": today}
    expenses.append(expense)

    print("Expence Added")

def show_coming_soon_label():  
    print("coming soon")

def main():
    expences = []
    while True:
        show_menu()
        choice = input("Choice: ")
        if choice == "1":
            add_expense(expences)
        elif choice == "2":
            show_coming_soon_label()
        elif choice == "3":
            show_coming_soon_label()
        elif choice == "4":
            print("Have a nice day! Goodbye :)") 
            break
        else:
            print(f"{choice} is invalid. Try again with [1, 2, 3, 4, 5]")

if __name__ == "__main__":
    main()

