from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from django.utils.html import format_html
from django.http import HttpResponse
import csv

from savings.models.fixed_savings import FixedSavings
from savings.models.target_savings import TargetSavings
from savings.models.fixed_deposit import FixedDeposit
from savings.models.investments import Investments
from savings.models.ledger import SavingsTransaction
from users.models import User

# ============================================================
#  INLINE: Transaction Ledger Inline Table
# ============================================================

class SavingsTransactionInline(GenericTabularInline):
    model = SavingsTransaction
    ct_field = "content_type"
    ct_fk_field = "object_id"
    extra = 0

    readonly_fields = ("date", "created_at", "amount_display", "transaction_type", "description")
    fields = ("transaction_type", "amount_display", "date", "description", "created_at")
    ordering = ("-date",)

    def amount_display(self, obj):
        color = "green" if obj.amount > 0 else "red"
        return format_html(f'<span style="color:{color}; font-weight:600;">₦{obj.amount:,.2f}</span>')
    amount_display.short_description = "Amount"

# ============================================================
#  BASE ADMIN (shared across all savings account types)
# ============================================================

class BaseSavingsAdmin(admin.ModelAdmin):
    inlines = [SavingsTransactionInline]
    readonly_fields = ("balance_display", "created_at", "updated_at")
    list_filter = ()
    search_fields = ("user_id",)
    ordering = ("-created_at",)
    actions = ["post_monthly_interest", "export_to_csv"]

    def balance_display(self, obj):
        return f"₦{obj.balance:,.2f}"
    balance_display.short_description = "Balance"

    # ----------------------------
    # Queryset filtering by ownership
    # ----------------------------
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Superusers see everything
        if request.user.is_superuser:
            return qs
        # Limit to accounts owned by the user
        return qs.filter(user=request.user)

    # ----------------------------
    # Role-based permissions
    # ----------------------------
    def has_change_permission(self, request, obj=None):
        if getattr(request.user, "is_viewer", lambda: False)():
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if getattr(request.user, "is_viewer", lambda: False)():
            return False
        return super().has_delete_permission(request, obj)

    def has_add_permission(self, request):
        if getattr(request.user, "is_viewer", lambda: False)():
            return False
        return super().has_add_permission(request)

    # ----------------------------
    # Admin actions
    # ----------------------------
    def post_monthly_interest(self, request, queryset):
        count = 0
        for account in queryset:
            # Only allow if superuser or owner
            if request.user.is_superuser or account.user == request.user:
                account.post_monthly_interest()
                count += 1
        self.message_user(request, f"Successfully posted interest for {count} account(s).")
    post_monthly_interest.short_description = "Post Monthly Interest"

    def export_to_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=savings_accounts.csv"
        writer = csv.writer(response)
        writer.writerow(["ID", "User ID", "Balance", "Interest Rate", "Created At"])
        for obj in queryset:
            if request.user.is_superuser or obj.user == request.user:
                writer.writerow([
                    obj.id,
                    obj.user_id,
                    float(obj.balance),
                    getattr(obj, "interest_rate", "—"),
                    obj.created_at,
                ])
        return response
    export_to_csv.short_description = "Export Selected to CSV"

# ============================================================
#  ACCOUNT ADMINS
# ============================================================

@admin.register(FixedSavings)
class FixedSavingsAdmin(BaseSavingsAdmin):
    list_display = ("user_id", "balance_display", "interest_rate", "created_at")

@admin.register(TargetSavings)
class TargetSavingsAdmin(BaseSavingsAdmin):
    list_display = ("user_id", "balance_display", "target_amount", "interest_rate", "created_at")

@admin.register(FixedDeposit)
class FixedDepositAdmin(BaseSavingsAdmin):
    list_display = ("user_id", "balance_display", "maturity_date", "interest_rate", "created_at")

@admin.register(Investments)
class InvestmentsAdmin(BaseSavingsAdmin):
    list_display = ("user_id", "balance_display", "created_at")

# ============================================================
#  SAVINGS TRANSACTION ADMIN (standalone)
# ============================================================

@admin.register(SavingsTransaction)
class SavingsTransactionAdmin(admin.ModelAdmin):
    list_display = ("account_link", "transaction_type", "amount", "date", "description", "created_at")
    list_filter = ("transaction_type", "date")
    search_fields = ("description", "content_type__model")
    actions = ["export_transactions_csv"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Limit transactions to accounts owned by the user
        return qs.filter(object_id__in=[acct.id for acct in FixedSavings.objects.filter(user=request.user)] +
                         [acct.id for acct in TargetSavings.objects.filter(user=request.user)] +
                         [acct.id for acct in FixedDeposit.objects.filter(user=request.user)] +
                         [acct.id for acct in Investments.objects.filter(user=request.user)])

    def account_link(self, obj):
        acct = obj.account
        if acct:
            return f"{acct.__class__.__name__} #{acct.pk} (User ID: {acct.user_id})"
        return "—"
    account_link.short_description = "Account"

    def export_transactions_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=savings_transactions.csv"
        writer = csv.writer(response)
        writer.writerow(["ID", "Account", "Type", "Amount", "Date", "Description"])
        for tx in queryset:
            # Only allow superuser or owner
            acct = tx.account
            if acct and (request.user.is_superuser or acct.user == request.user):
                writer.writerow([
                    tx.id,
                    tx.account,
                    tx.transaction_type,
                    float(tx.amount),
                    tx.date,
                    tx.description,
                ])
        return response
    export_transactions_csv.short_description = "Export to CSV"
