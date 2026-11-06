# Personal Finance Tracker

A Python command-line personal finance management application organized in a clean, layered architecture. Data is stored in CSV files using Python's built-in `csv` module; no third-party libraries or external databases are required.

---

## What's New

### 1. Manual Savings & Available Balance
- Add manual savings directly to any savings goal via **4. Savings Goals -> 2. Add savings to goal**.
- Savings are **not** counted as a personal expense.
- Savings are deducted from your **Available Balance**:
  $$\text{Net Balance} = \text{Income} - \text{Expenses}$$
  $$\text{Available Balance} = \text{Income} - \text{Expenses} - \text{Total Savings}$$
- Goal progress updates automatically.

### 2. Automatic Monthly Savings
- Automatically detects completed months when you log in or view the Dashboard.
- Calculates remaining unused money from that month:
  $$\text{Remaining Unused} = \text{Monthly Income} - \text{Monthly Expenses} - \text{Monthly Manual Savings}$$
- **Important**: Any money already manually allocated to savings during that month is subtracted so it is **never counted twice**.
- Asks for your permission before transferring. If you decline, no money is transferred.
- You can select which savings goal receives the funds.
- Transfers are recorded in `DATA/monthly_transfers.csv` to **prevent duplicate transfers**.

### 3. Financial Dashboard
Displays:
- **Total Income**, **Total Expenses**, and **Total Savings**
- **Net Balance** ($\text{Income} - \text{Expenses}$)
- **Available Balance** ($\text{Income} - \text{Expenses} - \text{Savings}$)
- **Budget Overview for Current Month**: Budget, Spent, Remaining, and Exceeded status.
- **Savings Goals Overview**: Target, Saved, Remaining, and Progress Percentage.

### 4. Current-Month Budgets
- Budgets track expenses for the **current calendar month** only.
- When a new month begins, budget tracking starts fresh without deleting previous transactions.
- Category matching is case-insensitive and ignores extra spaces.

---

## Folder Structure

```text
Personal_Finance_Tracker/
├── main.py
├── config.py
├── README.md
├── test_finance.py
├── DATA/
│   ├── users.csv
│   ├── transactions.csv
│   ├── budgets.csv
│   ├── savings_goals.csv
│   └── monthly_transfers.csv
└── smart_finance/
    ├── models/
    ├── services/
    │   └── finance_service.py
    ├── storage/
    │   ├── csv_store.py
    │   └── repositories.py
    ├── ui/
    │   ├── helpers.py
    │   ├── login.py
    │   └── menus.py
    └── utils/
        └── validation.py
```

---

## How to Run

1. Open the project folder in terminal or VS Code.
2. Run:
   ```bash
   python main.py
   ```
3. Register a new user or log in with an existing user.
4. Run automated tests at any time:
   ```bash
   python test_finance.py
   ```
