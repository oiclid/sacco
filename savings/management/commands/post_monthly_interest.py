from django.core.management.base import BaseCommand
from decimal import Decimal
from savings.models.fixed_savings import FixedSavings
from savings.models.target_savings import TargetSavings
from savings.models.fixed_deposit import FixedDeposit
from savings.models.investments import Investments
from savings.models.monthly_interest_report import MonthlyInterestReport
from django.utils import timezone

class Command(BaseCommand):
    help = "Post monthly interest for all savings accounts (run monthly via cron)."

    def handle(self, *args, **options):
        total_interest_all = Decimal("0.00")
        details = []
        summary = {}

        today = timezone.now().date()
        month_start = today.replace(day=1)

        for model_cls in [FixedSavings, TargetSavings, FixedDeposit, Investments]:
            accounts = model_cls.objects.all()
            total_interest = Decimal("0.00")
            accounts_processed = 0

            for acct in accounts:
                amt = acct.post_monthly_interest()
                if amt and amt != Decimal("0.00"):
                    total_interest += amt
                accounts_processed += 1
                details.append(f"{acct.__class__.__name__}#{acct.pk} user={acct.user.username} amt={amt}")

            summary[model_cls.__name__] = {
                "accounts_processed": accounts_processed,
                "total_interest": total_interest
            }
            total_interest_all += total_interest

            # Save report for this account type
            MonthlyInterestReport.objects.create(
                month=month_start,
                account_type=model_cls.__name__,
                accounts_processed=accounts_processed,
                total_interest=total_interest
            )

        self.stdout.write(self.style.SUCCESS(f"Total interest posted: ₦{total_interest_all:,.2f}"))
        for d in details:
            self.stdout.write(d)

