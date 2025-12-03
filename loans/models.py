from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal

# -------------------------------
# Loan Types & Status
# -------------------------------
LOAN_TYPES = [
    ("major", "Major"),
    ("car", "Car"),
    ("electronics", "Electronics"),
    ("land", "Land"),
    ("essential", "Essential Commodities"),
    ("education", "Education"),
    ("emergency", "Emergency"),
]

LOAN_STATUS = [
    ("pending", "Pending"),
    ("approved", "Approved"),
    ("disbursed", "Disbursed"),
    ("repaid", "Repaid"),
    ("defaulted", "Defaulted"),
]

LOAN_CONFIG = {
    "major": {"rate": 10, "term": 24},
    "car": {"rate": 15, "term": 36},
    "electronics": {"rate": 10, "term": 18},
    "land": {"rate": 10, "term": 24},
    "essential": {"rate": 10, "term": 12},
    "education": {"rate": 10, "term": 6},
    "emergency": {"rate": 5, "term": 4},
}


class Loan(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="loans"
    )
    loan_type = models.CharField(max_length=20, choices=LOAN_TYPES)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    term_months = models.PositiveIntegerField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=LOAN_STATUS, default="pending")
    disbursed_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.interest_rate or not self.term_months:
            config = LOAN_CONFIG.get(self.loan_type, {"rate": 10, "term": 12})
            self.interest_rate = config["rate"]
            self.term_months = config["term"]
        super().save(*args, **kwargs)

    @property
    def total_payable(self):
        return self.amount + (self.amount * self.interest_rate / 100)

    @property
    def total_repaid(self):
        return sum(r.amount for r in self.repayments.all())

    @property
    def outstanding(self):
        return self.total_payable - self.total_repaid

    @property
    def monthly_installment(self):
        if not self.term_months or self.term_months == 0:
            return Decimal("0.00")
        return self.total_payable / self.term_months

    def check_default(self):
        if self.status in ["disbursed", "approved"] and self.disbursed_at:
            due_date = self.disbursed_at + timezone.timedelta(days=30 * self.term_months)
            if timezone.now().date() > due_date and self.total_repaid < self.total_payable:
                self.status = "defaulted"
                self.save()

    def __str__(self):
        return f"Loan #{self.pk} ({self.user.username}) - {self.loan_type} - {self.status}"


class LoanRepayment(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name="repayments")
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    date = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.loan.total_repaid >= self.loan.total_payable:
            self.loan.status = "repaid"
            self.loan.save()

    def __str__(self):
        return f"Repayment #{self.pk} - Loan #{self.loan.pk} - ₦{self.amount:,.2f}"
