from django.db import models

class MonthlyInterestReport(models.Model):
    """
    Stores summary of interest posted for all accounts for a given month.
    """
    month = models.DateField()  # first day of the month
    account_type = models.CharField(max_length=50)
    accounts_processed = models.PositiveIntegerField()
    total_interest = models.DecimalField(max_digits=20, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Monthly Interest Report"
        verbose_name_plural = "Monthly Interest Reports"

    def __str__(self):
        return f"{self.month} - {self.account_type} - ₦{self.total_interest:,.2f}"

