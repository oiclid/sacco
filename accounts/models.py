from django.db import models
from django.utils import timezone
from decimal import Decimal

# Once other apps exist, uncomment these:
# from savings.models import SavingsAccount
# from loans.models import Loan
# from cash_dividends.models import CashTransaction, Dividend


class Member(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('quit', 'Quit'),
        ('retired', 'Retired'),
        ('deceased', 'Deceased'),
    ]

    registration_number = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100)

    join_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    shutdown_date = models.DateField(null=True, blank=True)
    shutdown_reason = models.CharField(max_length=50, null=True, blank=True)

    # Total amount payable to the member when account closes
    final_balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))

    class Meta:
        ordering = ("registration_number",)

    def __str__(self):
        return f"{self.registration_number} – {self.full_name()}"

    def full_name(self):
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"

    # --------------------------------------------------------------
    # ACCOUNT SHUTDOWN LOGIC
    # --------------------------------------------------------------
    def shutdown(self, reason):
        """
        Performs shutdown workflow:
        quit → apply quit fee
        retired → add retirement benefit
        deceased → distribute death levy + credit account
        """
        if reason not in ["quit", "retired", "deceased"]:
            raise ValueError("Invalid shutdown reason")

        self.status = reason
        self.shutdown_reason = reason
        self.shutdown_date = timezone.now()

        if reason == "quit":
            self.final_balance = self._process_quit()

        elif reason == "retired":
            self.final_balance = self._process_retirement()

        elif reason == "deceased":
            self.final_balance = self._process_death()

        self.save()
        return self.final_balance

    # --------------------------------------------------------------
    # SHUTDOWN SCENARIOS
    # --------------------------------------------------------------

    def _process_quit(self):
        """
        Quit:
        - apply quit fee (default: 2% of total savings)
        """
        total_savings = self.get_total_savings()
        fee = total_savings * Decimal("0.02")
        net = total_savings - fee

        # record transaction
        self._create_cash_transaction("quit_charge", -fee)

        return net

    def _process_retirement(self):
        """
        Retirement:
        - add retirement benefit (e.g., 10%)
        """
        total_savings = self.get_total_savings()
        bonus = total_savings * Decimal("0.10")
        net = total_savings + bonus

        self._create_cash_transaction("retirement_benefit", bonus)

        return net

    def _process_death(self):
        """
        Death:
        - charge all active members a fixed levy
        - add levy to deceased account
        """

        active_count = self.get_active_members_count()
        levy_per_member = Decimal("1000")  # example
        total_levy = active_count * levy_per_member

        # Deduct from other members
        self._charge_active_members(levy_per_member)

        # Record on deceased member
        self._create_cash_transaction("death_benefit", total_levy)

        return total_levy

    # --------------------------------------------------------------
    # STUB METHODS FOR OTHER APP INTEGRATIONS
    # --------------------------------------------------------------

    # SAVINGS APP
    def get_total_savings(self):
        """
        Returns total savings across:
        - fixed savings (premium)
        - target savings (special savings)
        - fixed deposit savings (flexible)
        - investments (shares)
        """
        # Example when savings app is ready:
        #
        # records = SavingsAccount.objects.filter(member=self)
        # return records.aggregate(total=Sum('balance'))['total'] or Decimal('0')

        return Decimal("50000.00")  # placeholder

    # LOANS APP
    def get_loans_outstanding(self):
        """
        Returns total loan outstanding.
        """
        # Example:
        # loans = Loan.objects.filter(member=self)
        # return loans.aggregate(total=Sum('remaining_balance'))['total'] or Decimal('0')
        return Decimal("20000.00")  # placeholder

    # CASH DIVIDENDS APP
    def get_dividends(self):
        """
        Total dividends received by this member.
        """
        # Example:
        # divs = Dividend.objects.filter(member=self)
        # return divs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        return Decimal("5000.00")  # placeholder

    # CASH TRANSACTIONS
    def _create_cash_transaction(self, category_code, amount):
        """
        Record cash movement in cash_dividends module.
        """
        # Example:
        # CashTransaction.objects.create(
        #     member=self,
        #     category=category_code,
        #     amount=amount
        # )
        pass

    def _charge_active_members(self, levy_amount):
        """
        Charge all active members for death levy.
        """
        # Example:
        # actives = Member.objects.filter(status='active')
        # for m in actives:
        #     CashTransaction.objects.create(
        #         member=m,
        #         category="death_levy",
        #         amount=-levy_amount
        #     )
        pass

    def get_active_members_count(self):
        """
        Count active members (excluding deceased member).
        """
        # Example:
        # return Member.objects.filter(status='active').count()

        return 100  # placeholder
