# run_budget_pipeline.py
from email_utils import build_email_dump
from budget_utils import update_budget_log
from send_utils import send_budget_update

def main():
    print("Fetching emails since Aug 23, 2025...")
    build_email_dump("2025-08-23")

    print("Updating grocery budget log...")
    update_budget_log()

    print("Sending budget update email...")
    send_budget_update()

    print("Pipeline completed successfully.")

if __name__ == "__main__":
    main()
