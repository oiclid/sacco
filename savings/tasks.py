import threading
import time
from datetime import datetime
import schedule
import logging
from django.utils import timezone

from savings.services.interest_service import post_all_monthly_interest
from savings.models.monthly_interest_report import MonthlyInterestReport

# Setup file logging
logging.basicConfig(
    filename="monthly_interest.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


def run_monthly_interest():
    """
    Post interest for all accounts, save reports, update ledger and interest history.
    """
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Running monthly interest posting...")
    summary = post_all_monthly_interest()
    today = timezone.now().date()
    month_start = today.replace(day=1)

    # Save reports and log
    for acct_type, data in summary.items():
        # Save to reports table
        MonthlyInterestReport.objects.create(
            month=month_start,
            account_type=acct_type,
            accounts_processed=data["accounts_processed"],
            total_interest=data["total_interest"]
        )

        # Log to file
        logging.info(f"{acct_type}: {data['accounts_processed']} accounts, "
                     f"Total interest: ₦{data['total_interest']:,.2f}")

        # Print to console
        print(f"{acct_type}: Processed {data['accounts_processed']} accounts, "
              f"Total interest: ₦{data['total_interest']:,.2f}")

    print("Monthly interest posting completed.\n")
    logging.info("Monthly interest posting completed.")


def schedule_monthly_interest():
    """
    Schedule `run_monthly_interest` to run automatically on the 1st day of every month at 00:00.
    Uses daily schedule and checks the day of the month.
    """
    def job():
        today = timezone.now().date()
        if today.day == 1:
            run_monthly_interest()

    # Schedule job to run every day at midnight
    schedule.every().day.at("00:00").do(job)

    # Run scheduler in a separate thread so it doesn't block Django
    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(60)  # check every minute

    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    print("Monthly interest scheduler started (running in background).")
