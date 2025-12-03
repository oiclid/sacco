from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Sum, Count
from django.utils import timezone

from .models import Loan
from .services.loans.loan_report_service import (
    generate_loan_report_queryset,
    export_loans_csv,
    export_loans_xlsx,
    export_loans_pdf,
)

# Allowed sortable columns (map user-friendly name to model field)
ALLOWED_SORT_FIELDS = {
    "id": "id",
    "amount": "amount",
    "interest_rate": "interest_rate",
    "term_months": "term_months",
    "status": "status",
    "created_at": "created_at",
    "total_repaid": None,  # handled client-side or by annotation if needed
    "outstanding": None,   # handled client-side or by annotation if needed
}


@login_required
def loan_report_view(request):
    """
    Display loan report with filtering, sorting, pagination, export.
    Also provides data used for charts. Sorting is via ?ordering=<field> (prefix '-' for desc).
    Pagination via ?page=<n>&per_page=<n>
    """
    user = request.user
    loan_type = request.GET.get("loan_type")
    status = request.GET.get("status")
    export_format = request.GET.get("export")  # csv / xlsx / pdf

    # Sorting
    ordering = request.GET.get("ordering", "-created_at")
    # sanitize ordering
    order_field = ordering.lstrip("-")
    if order_field not in ALLOWED_SORT_FIELDS:
        ordering = "-created_at"

    # Base filtered queryset
    base_qs = generate_loan_report_queryset(user=user, loan_type=loan_type, status=status)

    # If we wanted to sort by computed fields like total_repaid/outstanding we'd annotate;
    # for simplicity we sort by provided DB fields and let client-side search handle computed sorts.
    qs = base_qs.order_by(ordering)

    # Handle exports (export entire filtered queryset, ignoring pagination)
    if export_format == "csv":
        return export_loans_csv(base_qs)
    elif export_format == "xlsx":
        return export_loans_xlsx(base_qs)
    elif export_format == "pdf":
        return export_loans_pdf(base_qs)

    # Pagination
    per_page = request.GET.get("per_page", 25)
    try:
        per_page = int(per_page)
        if per_page <= 0:
            per_page = 25
    except (ValueError, TypeError):
        per_page = 25

    page = request.GET.get("page", 1)
    paginator = Paginator(qs, per_page)
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    # Choices for filters
    loan_types = [(lt[0], lt[1]) for lt in Loan.LOAN_TYPES]
    statuses = [(st[0], st[1]) for st in Loan.LOAN_STATUS]

    # Dashboard / chart aggregates (use base_qs unpaginated to reflect filters)
    all_loans = generate_loan_report_queryset(user=user)  # not filtered by selection, for global charts
    # If you'd prefer charts reflect the current filter, change to base_qs

    total_amount_by_type = all_loans.values("loan_type").annotate(total=Sum("amount"))
    total_amount_by_status = all_loans.values("status").annotate(total=Sum("amount"))
    loan_count_by_type = all_loans.values("loan_type").annotate(count=Count("id"))
    loan_count_by_status = all_loans.values("status").annotate(count=Count("id"))

    # Monthly trend (last 12 months)
    from django.db.models.functions import TruncMonth
    monthly = (
        all_loans.annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )

    # Latest loans (for side panel shortcut)
    latest_loans = all_loans.order_by("-created_at")[:10]

    context = {
        "page_obj": page_obj,
        "paginator": paginator,
        "loans": page_obj.object_list,  # template loops over loans
        "loan_types": loan_types,
        "statuses": statuses,
        "selected_type": loan_type,
        "selected_status": status,
        "ordering": ordering,
        "per_page": per_page,

        # Chart data (JSON-friendly; template will render as safe)
        "total_amount_by_type": list(total_amount_by_type),
        "total_amount_by_status": list(total_amount_by_status),
        "loan_count_by_type": list(loan_count_by_type),
        "loan_count_by_status": list(loan_count_by_status),
        "monthly_trend": [{"month": m["month"].strftime("%b %Y"), "count": m["count"]} for m in monthly],

        "total_amount": all_loans.aggregate(total=Sum("amount"))["total"] or 0,
        "total_repaid": all_loans.aggregate(total=Sum("repayments__amount"))["total"] or 0,
        "total_outstanding": (all_loans.aggregate(total=Sum("amount"))["total"] or 0) - (all_loans.aggregate(total=Sum("repayments__amount"))["total"] or 0),
        "latest_loans": latest_loans,
        "today": timezone.now().date(),
    }

    return render(request, "loans/loan_report.html", context)


@login_required
def loan_detail_json(request, pk):
    """
    Return JSON details for a loan (used by side panel).
    """
    loan = get_object_or_404(Loan, pk=pk)
    # Permission: non-admins may only view own loans
    if hasattr(request.user, "role") and not request.user.is_superadmin() and not request.user.is_admin():
        if loan.user_id != request.user.id:
            return JsonResponse({"error": "Forbidden"}, status=403)

    repayments = [
        {"id": r.pk, "amount": float(r.amount), "date": r.date.isoformat()}
        for r in loan.repayments.order_by("-date").all()
    ]
    data = {
        "id": loan.pk,
        "user": getattr(loan.user, "username", str(loan.user_id)),
        "loan_type": loan.loan_type,
        "amount": float(loan.amount),
        "interest_rate": float(loan.interest_rate or 0),
        "term_months": loan.term_months,
        "status": loan.status,
        "total_payable": float(loan.total_payable),
        "total_repaid": float(loan.total_repaid),
        "outstanding": float(loan.outstanding),
        "disbursed_at": loan.disbursed_at.isoformat() if loan.disbursed_at else None,
        "created_at": loan.created_at.isoformat(),
        "repayments": repayments,
    }
    return JsonResponse(data)
