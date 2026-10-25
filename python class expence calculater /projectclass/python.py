import os
import webbrowser
import time

def run_budget_tracker():
    print("--- 💰 SMART BUDGET TRACKER ---")
    
    # 1. Get Inputs
    try:
        name = input("Enter your name: ")
        income = float(input("Enter your Total Monthly Income (e.g. 5000): "))
    except ValueError:
        income = 0.0

    expenses = {}
    print("\n--- Enter Expenses (Type 'done' to finish) ---")
    while True:
        category = input("Expense Name (e.g. Rent): ")
        if category.lower() == 'done': break
        try:
            amt = float(input(f"Amount for {category}: "))
            expenses[category] = amt
        except ValueError: pass

    # 2. Calculations
    total_expenses = sum(expenses.values())
    savings = income - total_expenses
    
    # Prepare Data for Chart
    labels = list(expenses.keys())
    data = list(expenses.values())
    colors = ["#ff6384", "#36a2eb", "#cc65fe", "#ffce56", "#4bc0c0"]
    
    # Logic: Add savings to chart if positive
    if savings > 0:
        labels.append("Savings")
        data.append(savings)
        colors.append("#4ade80")
    
    status = "Healthy Finance 🟢" if savings > 0 else "Over Budget! 🔴"

    # 3. Write Data to a JS file
    # This acts as a bridge between Python and the Browser
    js_content = f"""
    const budgetData = {{
        name: "{name}",
        income: {income},
        expense: {total_expenses},
        savings: {savings},
        status: "{status}",
        labels: {labels},
        data: {data},
        colors: {colors}
    }};
    """
    
    with open("budget_data.js", "w", encoding="utf-8") as f:
        f.write(js_content)

    print("\n✅ Data processed! Opening Dashboard...")
    time.sleep(1)
    
    # Open index.html
    webbrowser.open('file://' + os.path.realpath("index.html"))

if __name__ == "__main__":
    run_budget_tracker()