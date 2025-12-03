# savings/admin_dashboard.py
from django.urls import path
from django.shortcuts import render
from django.contrib.admin import AdminSite
from django.db.models import Sum
from django.utils import timezone

from .models import (
    FixedSavingsAccount,
    TargetSavingsAccount,
    FixedDepositAccount,
    InvestmentAccount,
    SavingsTransaction,
)


def savings_dashboard(request):
    today = timezone.now().date()
    month_start = today.replace(day=1)

    total_balances = (
        FixedSavingsAccount.objects.aggregate(total=Sum("balance"))["total"] or 0
        + TargetSavingsAccount.objects.aggregate(total=Sum("balance"))["total"] or 0
        + FixedDepositAccount.objects.aggregate(total=Sum("balance"))["total"] or 0
        + InvestmentAccount.objects.aggregate(total=Sum("balance"))["total"] or 0
    )

    interest_this_month = SavingsTransaction.objects.filter(
        transaction_type="interest",
        date__gte=month_start,
    ).aggregate(total=Sum("amount"))["total"] or 0

    context = {
        "title": "Savings Dashboard",
        "total_balances": total_balances,
        "interest_this_month": interest_this_month,
        "active_fixed": FixedSavingsAccount.objects.filter(status="active").count(),
        "active_target": TargetSavingsAccount.objects.filter(status="active").count(),
        "active_fd": FixedDepositAccount.objects.filter(status="active").count(),
        "active_invest": InvestmentAccount.objects.filter(status="active").count(),
    }

    return render(request, "admin/savings_dashboard.html", context)
