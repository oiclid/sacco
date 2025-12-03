from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class AccountProfile(models.Model):
    """
    Stores account identity information used for reporting.
    Registration number is required and is unique.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="account_profile")
    registration_number = models.CharField(max_length=50, unique=True)

    first_name = models.CharField(max_length=50)
    middle_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["registration_number"]

    def __str__(self):
        return f"{self.registration_number} - {self.first_name} {self.last_name}"


class ReportCache(models.Model):
    """
    Optional caching of computed reports for faster charts, dashboards,
    and heavy analytics.
    """
    account = models.ForeignKey(AccountProfile, on_delete=models.CASCADE)
    period = models.DateField()  # As at (date)

    total_premium = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fixed_target_deposits = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shares_investment = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    major_loan = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    car_loan = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    electronics_loan = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    land_loan = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    essential_commodities_loan = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    education_loan = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    emergency_loan = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    total_loan_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("account", "period")

    def __str__(self):
        return f"Report Cache: {self.account} - {self.period}"
