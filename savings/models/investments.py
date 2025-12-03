from django.db import models
from django.conf import settings
from .ledger import SavingsTransaction
from .interest_history import InterestHistory

class Investments(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="investment_accounts"
    )
    balance = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def post_monthly_interest(self):
        # No interest for investments, but still log transaction for consistency
        SavingsTransaction.record(
            account=self,
            transaction_type="interest",
            amount=0,
            description="No interest for investments",
            
        )

        InterestHistory.objects.create(account=self, amount=0)

    def __str__(self):
        return f"Investments #{self.pk} ({self.user.username})"
