from django.contrib import admin
from django.utils.html import format_html
from django.http import HttpResponse
from django.utils import timezone
import io
from .models import Loan, LoanRepayment
from users.models import User
from .services.loans.loan_report_service import (
    export_loans_csv,
    export_loans_xlsx,
    export_loans_pdf,
    generate_loan_report_queryset,
)


class LoanRepaymentInline(admin.TabularInline):
    model = LoanRepayment
    extra = 0
    readonly_fields = ("date", "amount", "created_at")
    fields = ("date", "amount", "created_at")
    ordering = ("-date",)


class BaseLoanAdmin(admin.ModelAdmin):
    inlines = [LoanRepaymentInline]
    list_display = (
        "user_link",
        "loan_type",
        "amount_display",
        "interest_rate",
        "term_months",
        "status",
        "total_repaid_display",
        "outstanding_display",
        "created_at",
    )
    list_filter = ("loan_type", "status", "created_at")
    search_fields = ("user__username", "loan_type")
    ordering = ("-created_at",)
    actions = [
        "approve_loans",
        "disburse_loans",
        "mark_as_repaid",
        "export_csv",
        "export_xlsx",
        "export_pdf",
    ]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        for loan in qs:
            loan.check_default()
        if hasattr(request.user, "role") and not request.user.is_superadmin() and not request.user.is_admin():
            qs = qs.filter(user=request.user)
        return qs

    def user_link(self, obj):
        return f"{obj.user.username} ({obj.user.role})"
    user_link.short_description = "User"

    def amount_display(self, obj):
        color = "green" if obj.amount > 0 else "red"
        return format_html(f'<span style="color:{color}; font-weight:600;">₦{obj.amount:,.2f}</span>')
    amount_display.short_description = "Amount"

    def total_repaid_display(self, obj):
        return f"₦{obj.total_repaid:,.2f}"
    total_repaid_display.short_description = "Total Repaid"

    def outstanding_display(self, obj):
        return f"₦{obj.outstanding:,.2f}"
    outstanding_display.short_description = "Outstanding"

    def approve_loans(self, request, queryset):
        updated = queryset.update(status="approved")
        self.message_user(request, f"{updated} loan(s) approved.")
    approve_loans.short_description = "Approve selected loans"

    def disburse_loans(self, request, queryset):
        updated = queryset.update(status="disbursed", disbursed_at=timezone.now())
        self.message_user(request, f"{updated} loan(s) disbursed.")
    disburse_loans.short_description = "Disburse selected loans"

    def mark_as_repaid(self, request, queryset):
        updated = queryset.update(status="repaid")
        self.message_user(request, f"{updated} loan(s) marked as repaid.")
    mark_as_repaid.short_description = "Mark selected loans as repaid"

    def export_csv(self, request, queryset):
        qs = generate_loan_report_queryset(user=request.user)
        return export_loans_csv(qs)
    export_csv.short_description = "Export Selected to CSV"

    def export_xlsx(self, request, queryset):
        qs = generate_loan_report_queryset(user=request.user)
        return export_loans_xlsx(qs)
    export_xlsx.short_description = "Export Selected to XLSX"

    def export_pdf(self, request, queryset):
        qs = generate_loan_report_queryset(user=request.user)
        return export_loans_pdf(qs)
    export_pdf.short_description = "Export Selected to PDF"


@admin.register(Loan)
class LoanAdmin(BaseLoanAdmin):
    change_list_template = "admin/loans/loan/change_list.html"

    def changelist_view(self, request, extra_context=None):
        qs = self.get_queryset(request)

        # Monthly trend
        monthly = (
            qs.annotate(month=TruncMonth("created_at"))
                .values("month")
                .annotate(count=Count("id"))
                .order_by("month")
        )

        extra_context["monthly_trend"] = [
            {"month": m["month"].strftime("%b %Y"), "count": m["count"]}
            for m in monthly
        ]

        extra_context["total_amount_by_type"] = list(
            qs.values("loan_type").annotate(total=Sum("amount"))
        )
        extra_context["loan_count_by_type"] = list(
            qs.values("loan_type").annotate(count=Count("id"))
        )
        extra_context["loan_count_by_status"] = list(
            qs.values("status").annotate(count=Count("id"))
        )
        stats = {
            "total_loans": qs.count(),
            "total_repaid": sum(l.total_repaid for l in qs),
            "total_outstanding": sum(l.outstanding for l in qs),
            "defaulted": qs.filter(status="defaulted").count(),
            "active": qs.exclude(status__in=["repaid", "defaulted"]).count(),
        }
        extra_context = extra_context or {}
        extra_context["stats"] = stats
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(LoanRepayment)
class LoanRepaymentAdmin(admin.ModelAdmin):
    list_display = ("loan", "amount", "date", "created_at")
    list_filter = ("date", "created_at")
    search_fields = ("loan__user__username", "loan__loan_type")
    ordering = ("-date",)
