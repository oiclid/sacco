from savings.models.fixed_savings import FixedSavings
from savings.models.target_savings import TargetSavings
from savings.models.fixed_deposit import FixedDeposit
from savings.models.investments import Investments
from django.utils import timezone
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

ACCOUNT_CLASSES = [FixedSavings, TargetSavings, FixedDeposit, Investments]

def post_all_monthly_interest():
    """
    Loop through all savings accounts and post monthly interest.
    Logs summary of total interest posted per account type.
    """
    today = timezone.now().date()
    summary = {}

    for cls in ACCOUNT_CLASSES:
        total_interest = Decimal("0.00")
        accounts = cls.objects.all()
        for account in accounts:
            prev_balance = account.balance
            account.post_monthly_interest()
            interest_posted = account.balance - prev_balance
            total_interest += interest_posted

        summary[cls.__name__] = {
            "accounts_processed": len(accounts),
            "total_interest": total_interest
        }

    for acct_type, data in summary.items():
        logger.info(
            f"[{today}] Posted interest for {data['accounts_processed']} "
            f"{acct_type} accounts. Total interest: ₦{data['total_interest']:,.2f}"
        )

    return summary
