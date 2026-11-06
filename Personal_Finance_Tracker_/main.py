from smart_finance.ui.login import start_login
from smart_finance.ui.menus import run_main_menu
from smart_finance.services import finance_service

if __name__ == "__main__":
    username = start_login()
    if username:
        finance_service.set_user(username)
        run_main_menu()
