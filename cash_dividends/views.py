from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.db.models import Sum, Count
from django.utils import timezone
from .models import SavingsAccount, Transaction
from .services.savings_report_service import (
    generate_savings_report_queryset,
    export_savings_csv,
    export_savings_xlsx,
    export_savings_pdf,
)

@login_required
def savings_report_view(request):
    """
    Display savings, dividends, withdrawals, and charges report with filtering.
    Supports CSV, XLSX, PDF exports, pagination, and dashboard charts.
    """
    user = request.user
    account_type = request.GET.get("account_type")
    transaction_type = request.GET.get("transaction_type")
    page_number = request.GET.get("page", 1)
    export_format = request.GET.get("export")  # csv / xlsx / pdf

    # -------------------------
    # Filtered querysets via service
    # -------------------------
    accounts_qs, transactions_qs = generate_savings_report_queryset(
        account_type=account_type,
        transaction_type=transaction_type,
    )

    # -------------------------
    # Handle exports
    # -------------------------
    if export_format == "csv":
        return export_savings_csv(accounts_qs, transactions_qs)
    elif export_format == "xlsx":
        return export_savings_xlsx(accounts_qs, transactions_qs)
    elif export_format == "pdf":
        return export_savings_pdf(accounts_qs, transactions_qs)

    # -------------------------
    # Pagination
    # -------------------------
    accounts_paginator = Paginator(accounts_qs, 20)
    transactions_paginator = Paginator(transactions_qs, 50)

    accounts_page = accounts_paginator.get_page(page_number)
    transactions_page = transactions_paginator.get_page(page_number)

    # -------------------------
    # Dashboard / summary stats
    # -------------------------
    total_balance = accounts_qs.aggregate(total=Sum("balance"))["total"] or 0
    total_dividends = accounts_qs.aggregate(total=Sum("total_dividends"))["total"] or 0
    total_withdrawals = accounts_qs.aggregate(total=Sum("total_withdrawals"))["total"] or 0
    total_charges = accounts_qs.aggregate(total=Sum("total_charges"))["total"] or 0

    account_count_by_type = accounts_qs.values("account_type").annotate(count=Count("id"))
    transaction_sum_by_type = transactions_qs.values("transaction_type").annotate(total=Sum("amount"))

    # -------------------------
    # Dropdown options
    # -------------------------
    ACCOUNT_TYPES = [
        ("special", "Special Savings"),
        ("fixed", "Fixed Deposit"),
        ("death", "Death Benefit Account"),
    ]

    TRANSACTION_TYPES = [
        ("cash_receipt", "Cash Receipts"),
        ("savings_withdrawal", "Savings Withdrawal"),
        ("dividend", "Dividends"),
        ("withdrawal_benefit", "Withdrawal Benefits"),
        ("death_charge", "Death Charges"),
        ("default_charge", "Default Charges"),
    ]

    context = {
        "accounts": accounts_page,
        "transactions": transactions_page,
        "account_types": ACCOUNT_TYPES,
        "transaction_types": TRANSACTION_TYPES,
        "selected_account_type": account_type,
        "selected_transaction_type": transaction_type,
        "today": timezone.now().date(),
        # Dashboard stats
        "total_balance": total_balance,
        "total_dividends": total_dividends,
        "total_withdrawals": total_withdrawals,
        "total_charges": total_charges,
        "account_count_by_type": list(account_count_by_type),
        "transaction_sum_by_type": list(transaction_sum_by_type),
        # Pagination objects
        "accounts_paginator": accounts_paginator,
        "transactions_paginator": transactions_paginator,
    }

    return render(request, "cash_dividends/savings_report.html", context)
