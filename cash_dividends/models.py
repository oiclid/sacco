from django.db import models
from django.conf import settings
from decimal import Decimal
from django.utils import timezone

# -------------------------------
# Account Types
# -------------------------------
ACCOUNT_TYPES = [
    ("special", "Special Savings"),
    ("fixed", "Fixed Deposit"),
    ("death", "Death Benefit Account"),
]

TRANSACTION_TYPES = [
    ("dividend", "Dividend"),
    ("withdrawal", "Withdrawal"),
    ("withdrawal_benefit", "Withdrawal Benefit"),
    ("death_charge", "Death Charge"),
    ("default_charge", "Default Charge"),
    ("cash_receipt", "Cash Receipt"),
]


class SavingsAccount(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="savings_accounts")
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    balance = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Computed properties
    @property
    def total_dividends(self):
        return sum(t.amount for t in self.transactions.filter(transaction_type="dividend"))

    @property
    def total_withdrawals(self):
        return sum(t.amount for t in self.transactions.filter(transaction_type__in=["withdrawal","withdrawal_benefit"]))

    @property
    def total_charges(self):
        return sum(t.amount for t in self.transactions.filter(transaction_type__in=["death_charge","default_charge"]))

    def __str__(self):
        return f"{self.user.username} - {self.account_type} - ₦{self.balance:,.2f}"


class Transaction(models.Model):
    account = models.ForeignKey(SavingsAccount, on_delete=models.CASCADE, related_name="transactions")
    transaction_type = models.CharField(max_length=30, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    date = models.DateField(auto_now_add=True)
    description = models.TextField(blank=True, null=True)
    related_account = models.ForeignKey(
        SavingsAccount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="related_transactions",
        help_text="For death benefits or charges applied to another account"
    )

    def save(self, *args, **kwargs):
        # Auto-adjust account balance
        if self.transaction_type in ["withdrawal", "withdrawal_benefit", "death_charge", "default_charge"]:
            self.amount = abs(self.amount) * -1  # Debit
        elif self.transaction_type in ["dividend", "cash_receipt"]:
            self.amount = abs(self.amount)  # Credit

        super().save(*args, **kwargs)

        # Update account balance
        self.account.balance = sum(t.amount for t in self.account.transactions.all())
        self.account.save()

        # If death_charge, also credit related account
        if self.transaction_type == "death_charge" and self.related_account:
            self.related_account.balance += abs(self.amount)
            self.related_account.save()

    def __str__(self):
        return f"{self.transaction_type} - ₦{self.amount:,.2f} ({self.account})"
