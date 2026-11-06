import streamlit as st
from smart_finance.services import finance_service

st.set_page_config(page_title="Personal Finance Tracker", layout="wide")
st.title("Personal Finance Tracker")

username = st.sidebar.text_input("Username")

if username:
    finance_service.set_user(username)

    page = st.sidebar.radio(
        "Go to",
        ["Dashboard", "Transactions", "Budgets", "Savings Goals"]
    )

    if page == "Dashboard":
        income, expenses, savings, net, available = finance_service.totals()

        col1, col2, col3 = st.columns(3)
        col1.metric("Income", f"₹{income:,.2f}")
        col2.metric("Expenses", f"₹{expenses:,.2f}")
        col3.metric("Available balance", f"₹{available:,.2f}")

        st.subheader("Budgets this month")
        st.dataframe(finance_service.budget_status(), use_container_width=True)

        st.subheader("Savings goals")
        st.dataframe(
            finance_service.savings_goal_overview(),
            use_container_width=True
        )

    elif page == "Transactions":
        st.info("Next, add a form here to record income and expenses.")

    elif page == "Budgets":
        st.info("Next, add a form here to create and view budgets.")

    elif page == "Savings Goals":
        st.info("Next, add a form here to create goals and record savings.")
else:
    st.write("Enter your username in the sidebar to view your finances.")