from datetime import date
from django.db.models import Sum
from ..models import AccountProfile, ReportCache

# -------------------------------
# Loan Categories (linked to Loan app)
# -------------------------------

LOAN_CATEGORIES = {
    "major": "Major Loan",
    "car": "Car Loan",
    "electronics": "Electronics Loan",
    "land": "Land Loan",
    "essential_commodities": "Essential Commodities Loan",
    "education": "Education Loan",
    "emergency": "Emergency Loan",
}

# ----------------------------------------------
# HELPERS: Hook into the real apps (Savings, Loans, Shares)
# ----------------------------------------------

def get_savings_totals(account_user):
    """
    Returns dict of:
    - total premium
    - fixed & target deposits
    - share investments
    """
    # TODO: Plug in the real Savings models
    from savings.models import SavingsAccount

    accounts = SavingsAccount.objects.filter(user=account_user)

    return {
        "total_premium": accounts.aggregate(total=Sum("balance"))["total"] or 0,
        "fixed_target_deposits": accounts.filter(account_type="fixed").aggregate(total=Sum("balance"))["total"] or 0,
        "shares_investment": accounts.filter(account_type="shares").aggregate(total=Sum("balance"))["total"] or 0,
    }


def get_loan_totals(account_user):
    """
    Returns loan balances grouped by category.
    """
    # TODO: Plug in the real Loan models
    from loans.models import LoanAccount

    data = {}
    total_balance = 0

    for key in LOAN_CATEGORIES.keys():
        amount = (
            LoanAccount.objects.filter(user=account_user, loan_type=key)
            .aggregate(total=Sum("balance"))["total"]
            or 0
        )
        data[key] = amount
        total_balance += amount

    data["total_balance"] = total_balance
    return data


# ----------------------------------------------
# MAIN REPORT BUILDER
# ----------------------------------------------

def build_account_report(account_profile: AccountProfile, as_at: date):
    """
    Generates the full structured report used for:
    - PDF exports
    - Excel exports
    - Dashboard charts
    - Account ledger table
    - “As at (date)” table
    """

    user = account_profile.user

    # Get savings data
    savings = get_savings_totals(user)

    # Get loan data
    loans = get_loan_totals(user)

    # Final net balance
    net_balance = (
        savings["total_premium"]
        + savings["fixed_target_deposits"]
        + savings["shares_investment"]
        - loans["total_balance"]
    )

    # Structure response
    report = {
        "as_at": as_at,
        "account": {
            "registration_number": account_profile.registration_number,
            "name": f"{account_profile.first_name} {account_profile.last_name}",
        },
        "savings": {
            "total_premium": savings["total_premium"],
            "fixed_target_deposits": savings["fixed_target_deposits"],
            "shares_investment": savings["shares_investment"],
        },
        "loans": {
            **{cat: loans[cat] for cat in LOAN_CATEGORIES.keys()},
            "total_loan_balance": loans["total_balance"],
        },
        "net_balance": net_balance,
    }

    return report


# ----------------------------------------------
# SAVE CACHE
# ----------------------------------------------

def cache_report(account_profile: AccountProfile, report: dict):
    """
    Creates or updates the monthly/period report cache.
    """
    period = report["as_at"]

    obj, created = ReportCache.objects.update_or_create(
        account=account_profile,
        period=period,
        defaults={
            "total_premium": report["savings"]["total_premium"],
            "fixed_target_deposits": report["savings"]["fixed_target_deposits"],
            "shares_investment": report["savings"]["shares_investment"],

            "major_loan": report["loans"]["major"],
            "car_loan": report["loans"]["car"],
            "electronics_loan": report["loans"]["electronics"],
            "land_loan": report["loans"]["land"],
            "essential_commodities_loan": report["loans"]["essential_commodities"],
            "education_loan": report["loans"]["education"],
            "emergency_loan": report["loans"]["emergency"],

            "total_loan_balance": report["loans"]["total_loan_balance"],
            "net_balance": report["net_balance"],
        }
    )
    return obj
