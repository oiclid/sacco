from django.db import models
from django.conf import settings
from .ledger import SavingsTransaction
from .interest_history import InterestHistory

class TargetSavings(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="target_savings_accounts"
    )
    balance = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=6.0)  # monthly %
    target_amount = models.DecimalField(max_digits=20, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def post_monthly_interest(self):
        interest = self.balance * (self.interest_rate / 100)
        self.balance += interest
        self.save()

        # Record transaction
        SavingsTransaction.record(
            account=self,
            transaction_type="interest",
            amount=interest,
            description="Monthly interest posting"
        )

        # Record interest history
        InterestHistory.objects.create(account=self, amount=interest)

    def __str__(self):
        return f"TargetSavings #{self.pk} ({self.user.username})"
