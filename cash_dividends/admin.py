# cash_dividends/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import SavingsAccount, Transaction
from django.utils import timezone

class TransactionInline(admin.TabularInline):
    model = Transaction
    fk_name = "account"
    extra = 0
    readonly_fields = ("date", "amount", "transaction_type", "related_account", "description")
    fields = ("date", "transaction_type", "amount", "related_account", "description")
    ordering = ("-date",)


@admin.register(SavingsAccount)
class SavingsAccountAdmin(admin.ModelAdmin):
    inlines = [TransactionInline]
    list_display = (
        "user",
        "account_type",
        "balance_display",
        "total_dividends_display",
        "total_withdrawals_display",
        "total_charges_display",
        "is_active",
    )
    list_filter = ("account_type", "is_active")
    search_fields = ("user__username", "account_type")
    ordering = ("-created_at",)
    change_list_template = "admin/cash_dividends/savingsaccount/change_list.html"

    # ---------------- DISPLAY HELPERS ---------------- #

    def balance_display(self, obj):
        color = "green" if obj.balance >= 0 else "red"
        return format_html(
            '<span style="color:{}; font-weight:600;">₦{:,.2f}</span>',
            color,
            obj.balance,
        )
    balance_display.short_description = "Balance"

    def total_dividends_display(self, obj):
        return f"₦{obj.total_dividends:,.2f}"
    total_dividends_display.short_description = "Total Dividends"

    def total_withdrawals_display(self, obj):
        return f"₦{obj.total_withdrawals:,.2f}"
    total_withdrawals_display.short_description = "Total Withdrawals"

    def total_charges_display(self, obj):
        return f"₦{obj.total_charges:,.2f}"
    total_charges_display.short_description = "Total Charges"

    # ---------------- CHANGE LIST (Dashboard) ---------------- #

    def changelist_view(self, request, extra_context=None):

        # Prefetch to avoid N+1 queries
        qs = (
            self.get_queryset(request)
            .select_related("user")
            .prefetch_related("transaction_set")
        )

        # Dashboard stats
        stats = {
            "total_balances": sum(a.balance for a in qs),
            "total_dividends": sum(a.total_dividends for a in qs),
            "total_withdrawals": sum(a.total_withdrawals for a in qs),
            "total_charges": sum(a.total_charges for a in qs),
            "active_accounts": qs.filter(is_active=True).count(),
            "inactive_accounts": qs.filter(is_active=False).count(),
        }

        # JSON-safe account data
        accounts_json = []
        for account in qs:
            accounts_json.append({
                "id": account.id,
                "user": account.user.username,
                "account_type": account.account_type,
                "balance": float(account.balance),
                "total_dividends": float(account.total_dividends),
                "total_withdrawals": float(account.total_withdrawals),
                "total_charges": float(account.total_charges),

                "transactions": [
                    {
                        "id": tx.id,
                        "date": tx.date.strftime("%Y-%m-%d"),
                        "amount": float(tx.amount),
                        "transaction_type": tx.transaction_type,
                        "related_account": tx.related_account.id if tx.related_account else None,
                        "description": tx.description,
                    }
                    for tx in account.transaction_set.all()
                ],
            })

        extra_context = extra_context or {}
        extra_context["dashboard"] = stats
        extra_context["accounts_json"] = accounts_json

        return super().changelist_view(request, extra_context=extra_context)

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("account", "transaction_type", "amount_display", "date", "related_account", "description")
    list_filter = ("transaction_type", "date")
    search_fields = ("account__user__username", "transaction_type")
    ordering = ("-date",)

    def amount_display(self, obj):
        color = "green" if obj.amount >= 0 else "red"
        return format_html(f'<span style="color:{color}; font-weight:600;">₦{obj.amount:,.2f}</span>')
    amount_display.short_description = "Amount"
