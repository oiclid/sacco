import csv
import json
from datetime import date, datetime
import io
from openpyxl import Workbook
from django.template.loader import render_to_string
from weasyprint import HTML

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views import View

from .models import AccountProfile, ReportCache
from .services.report_builder import (
    build_account_report,
    cache_report,
    LOAN_CATEGORIES,
)

# =========================================================
# UTIL EXPORTERS
# =========================================================


def export_csv(report, filename="report.csv"):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)

    # Header
    writer.writerow(["Report Date", report.get("as_at", "")])
    if "account" in report:
        writer.writerow(["Account", report["account"]["name"]])
    writer.writerow([])

    # Savings
    savings_data = report.get("savings_totals") or report.get("savings", {})
    if savings_data:
        writer.writerow(["SAVINGS"])
        for k, v in savings_data.items():
            writer.writerow([k.replace("_", " ").title(), v])

    # Loans
    loan_data = report.get("loan_totals") or report.get("loans", {})
    if loan_data:
        writer.writerow([])
        writer.writerow(["LOANS"])
        for k, v in loan_data.items():
            if k != "total_loan_balance":
                writer.writerow([k.replace("_", " ").title(), v])
        writer.writerow(["Total Loan Balance", loan_data.get("total_loan_balance", 0)])

    # Net balance / total
    if "net_balance" in report:
        writer.writerow([])
        writer.writerow(["Net Balance", report["net_balance"]])
    if "total" in report:
        writer.writerow([])
        writer.writerow(["Total", report["total"]])

    return response


def export_json(report):
    return JsonResponse(report, safe=False)


def export_xlsx(report, filename="report.xlsx"):
    wb = Workbook()
    ws = wb.active
    ws.title = "Report"

    # Header
    ws.append(["Report Date", report.get("as_at", "")])
    ws.append([])

    # Summary
    summary = report.get("summary", {})
    ws.append(["TOTAL ACCOUNTS", summary.get("total_accounts", 0)])
    ws.append(["TOTAL SAVINGS", summary.get("total_savings", 0)])
    ws.append(["TOTAL LOANS", summary.get("total_loans", 0)])
    ws.append(["NET POSITION", summary.get("net_position", 0)])
    ws.append([])

    # Savings
    savings_totals = report.get("savings_totals", {})
    if savings_totals:
        ws.append(["SAVINGS BREAKDOWN"])
        for k, v in savings_totals.items():
            ws.append([k.replace("_", " ").title(), v])
        ws.append([])

    # Loans
    loan_totals = report.get("loan_totals", {})
    if loan_totals:
        ws.append(["LOANS BREAKDOWN"])
        for k, v in loan_totals.items():
            ws.append([k.replace("_", " ").title(), v])
        ws.append([])

    # Rows
    rows = report.get("rows", [])
    if rows:
        ws.append(["ACCOUNT", "NET BALANCE"])
        for r in rows:
            ws.append([getattr(r["account"], "registration_number", "N/A"), r.get("net_balance", 0)])

    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response


def export_pdf(report, filename="report.pdf"):
    html_string = render_to_string("reports/pdf/as_at_report.html", {"report": report})
    pdf_file = HTML(string=html_string).write_pdf()
    response = HttpResponse(pdf_file, content_type="application/pdf")
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# =========================================================
# HELPER: Determine export format
# =========================================================

def handle_export(request, report, filename="report"):
    fmt = request.GET.get("export")

    if fmt == "csv":
        return export_csv(report, filename + ".csv")
    if fmt == "json":
        return export_json(report)
    if fmt == "xlsx":
        return export_xlsx(report, filename + ".xlsx")
    if fmt == "pdf":
        return export_pdf(report, filename + ".pdf")

    return None


# =========================================================
# ACCOUNT LEDGER REPORT
# =========================================================

class AccountLedgerView(View):
    """
    URL: /reports/ledger/<account_id>/?as_at=2024-12-31
    Shows:
      - savings categories
      - loan categories
      - net position
      - chart-ready JSON
    """

    def get(self, request, account_id):
        as_at_str = request.GET.get("as_at")
        if as_at_str:
            try:
                as_at = datetime.strptime(as_at_str, "%Y-%m-%d").date()
            except:
                as_at = date.today()
        else:
            as_at = date.today()

        profile = get_object_or_404(AccountProfile, id=account_id)

        # Build report
        report = build_account_report(profile, as_at)

        # Save into cache
        cache_report(profile, report)

        # Handle CSV / JSON / PDF export
        export_response = handle_export(
            request,
            report={
                "as_at": as_at.isoformat(),
                "account": {"name": f"{profile.first_name} {profile.last_name}"},
                "savings": report["savings"],
                "loans": report["loans"],
                "net_balance": report["net_balance"],
            },
            filename=f"account_{profile.registration_number}_ledger"
        )
        if export_response:
            return export_response
        # Render template
        return render(
            request,
            "reports/account_ledger.html",
            {
                "account": profile,
                "report": report,
                "loan_categories": LOAN_CATEGORIES,
            },
        )

# =========================================================
# Generic integration pattern for all report views
# =========================================================

def exportable_view(view_func):
    """
    Decorator to automatically handle CSV/JSON/XLSX/PDF exports.
    Usage: decorate the view's GET method with @exportable_view
    """

    def wrapper(self, request, *args, **kwargs):
        result = view_func(self, request, *args, **kwargs)
        # If view returned a dict and has 'report', handle export
        if isinstance(result, dict) and "report" in result:
            export_response = handle_export(request, result["report"], filename=result.get("filename", "report"))
            if export_response:
                return export_response
        return result  # Either HttpResponse or render
    return wrapper


# =========================================================
# CASHBOOK REPORT
# =========================================================

class CashbookReportView(View):
    """
    URL: /reports/cashbook/
    Lists all transactions across:
        - Savings
        - Loans
        - Any other financial movements
    """

    def get(self, request):

        from savings.models import Transaction as SavingsTx
        from loans.models import LoanTransaction as LoanTx

        # All savings transactions
        savings_tx = SavingsTx.objects.all().order_by("-date")

        # All loan transactions
        loan_tx = LoanTx.objects.all().order_by("-date")

        # Merge into one list
        combined = []

        for s in savings_tx:
            combined.append({
                "date": s.date,
                "type": f"Savings ({s.transaction_type})",
                "amount": s.amount,
                "user": s.account.user.username,
            })

        for l in loan_tx:
            combined.append({
                "date": l.date,
                "type": f"Loan ({l.tx_type})",
                "amount": l.amount,
                "user": l.account.user.username,
            })

        # Sort by newest
        combined = sorted(combined, key=lambda x: x["date"], reverse=True)

        # Export if needed
        if request.GET.get("export") == "csv":
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = "attachment; filename=cashbook.csv"
            writer = csv.writer(response)
            writer.writerow(["Date", "User", "Type", "Amount"])
            for row in combined:
                writer.writerow([row["date"], row["user"], row["type"], row["amount"]])
            return response

        return render(request, "reports/cashbook.html", {"rows": combined})


# =========================================================
# "AS AT" MASTER SUMMARY FOR ALL ACCOUNTS
# =========================================================

class AsAtSummaryView(View):
    """
    URL: /reports/as_at/?date=2024-12-31
    Produces:
       | Account ID | Savings | Loans | Net Position |
    """

    def get(self, request):
        date_str = request.GET.get("date")
        if date_str:
            try:
                as_at = datetime.strptime(date_str, "%Y-%m-%d").date()
            except:
                as_at = date.today()
        else:
            as_at = date.today()

        rows = []

        for account in AccountProfile.objects.all():
            report = build_account_report(account, as_at)
            cache_report(account, report)

            rows.append({
                "account": account,
                "savings": sum(report["savings"].values()),
                "loan_balance": report["loans"]["total_loan_balance"],
                "net": report["net_balance"],
            })

        # Export CSV
        if request.GET.get("export") == "csv":
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = "attachment; filename=as_at_summary.csv"
            writer = csv.writer(response)
            writer.writerow(["Account", "Savings Total", "Loan Balance", "Net Balance"])
            for r in rows:
                writer.writerow([
                    r["account"].registration_number,
                    r["savings"],
                    r["loan_balance"],
                    r["net"],
                ])
            return response

        return render(
            request,
            "reports/as_at.html",
            {"rows": rows, "as_at": as_at}
        )


# =========================================================
# DASHBOARD (Graphs + Cached Totals)
# =========================================================

class ReportsDashboardView(View):
    """
    URL: /reports/dashboard/
    Displays:
        - loan categories pie chart
        - savings vs loans bar chart
        - total accounts
        - highest deposits
        - highest loan exposure
    """

    def get(self, request):

        # Load cached data
        cached = ReportCache.objects.all()

        # Aggregate per category
        loan_totals = {cat: 0 for cat in LOAN_CATEGORIES.keys()}
        savings_total = 0
        loan_total = 0

        for r in cached:
            savings_total += (
                r.total_premium +
                r.fixed_target_deposits +
                r.shares_investment
            )
            loan_total += r.total_loan_balance

            # Per-category
            loan_totals["major"] += r.major_loan
            loan_totals["car"] += r.car_loan
            loan_totals["electronics"] += r.electronics_loan
            loan_totals["land"] += r.land_loan
            loan_totals["essential_commodities"] += r.essential_commodities_loan
            loan_totals["education"] += r.education_loan
            loan_totals["emergency"] += r.emergency_loan

        # Chart-friendly structure
        chart_data = {
            "loan_category_labels": list(LOAN_CATEGORIES.values()),
            "loan_category_totals": list(loan_totals.values()),
            "savings_total": savings_total,
            "loan_total": loan_total,
        }

        # Return in template
        return render(
            request,
            "reports/dashboard.html",
            {"chart_data": json.dumps(chart_data)},
        )

# =========================================================
# MONTHLY REPAYMENTS REPORT
# =========================================================

class MonthlyRepaymentsView(View):
    """
    URL: /reports/monthly_repayments/?month=2024-12
    Shows all loan repayments grouped by month.
    """

    def get(self, request):

        from loans.models import LoanTransaction

        month_str = request.GET.get("month")
        if not month_str:
            return HttpResponse("Missing ?month=YYYY-MM", status=400)

        year, month = month_str.split("-")
        year = int(year)
        month = int(month)

        # Filter repayments only
        repayments = LoanTransaction.objects.filter(
            date__year=year, date__month=month, tx_type="repayment"
        ).order_by("-date")

        total_amount = sum(r.amount for r in repayments)

        # CSV export
        if request.GET.get("export") == "csv":
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = f"attachment; filename=repayments_{month_str}.csv"
            writer = csv.writer(response)
            writer.writerow(["Date", "Account", "Loan Type", "Amount"])

            for r in repayments:
                writer.writerow([r.date, r.account.user.username, r.loan.category, r.amount])

            writer.writerow([])
            writer.writerow(["TOTAL", total_amount])
            return response

        return render(
            request,
            "reports/monthly_repayments.html",
            {"rows": repayments, "total": total_amount, "month": month_str},
        )


# =========================================================
# MONTHLY DISBURSEMENTS REPORT
# =========================================================

class MonthlyDisbursementsView(View):
    """
    URL: /reports/monthly_disbursements/?month=2024-12
    """

    def get(self, request):

        from loans.models import LoanTransaction

        month_str = request.GET.get("month")
        if not month_str:
            return HttpResponse("Missing ?month=YYYY-MM", status=400)

        year, month = month_str.split("-")
        year = int(year)
        month = int(month)

        # Loan disbursals
        disb = LoanTransaction.objects.filter(
            date__year=year, date__month=month, tx_type="disbursement"
        ).order_by("-date")

        total_disb = sum(d.amount for d in disb)

        # Export
        if request.GET.get("export") == "csv":
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = f"attachment; filename=disbursements_{month_str}.csv"
            writer = csv.writer(response)
            writer.writerow(["Date", "Account", "Loan Type", "Amount"])
            for d in disb:
                writer.writerow([d.date, d.account.user.username, d.loan.category, d.amount])
            writer.writerow([])
            writer.writerow(["TOTAL", total_disb])
            return response

        return render(
            request,
            "reports/monthly_disbursements.html",
            {"rows": disb, "total": total_disb, "month": month_str},
        )


# =========================================================
# MONTHLY REVENUE REPORT
# =========================================================

class MonthlyRevenueView(View):
    """
    URL: /reports/monthly_revenue/?month=2024-12
    Revenue sources:
        - Loan interest
        - Penalties
        - Dividends earned (if applicable)
    """

    def get(self, request):

        from loans.models import LoanTransaction
        from cash_dividends.models import DividendPayment

        month_str = request.GET.get("month")
        if not month_str:
            return HttpResponse("Missing ?month=YYYY-MM", status=400)

        year, month = map(int, month_str.split("-"))

        # Interest earned
        interest_tx = LoanTransaction.objects.filter(
            date__year=year, date__month=month, tx_type="interest"
        )

        interest_total = sum(i.amount for i in interest_tx)

        # Penalties
        penalties_tx = LoanTransaction.objects.filter(
            date__year=year, date__month=month, tx_type="penalty"
        )
        penalties_total = sum(p.amount for p in penalties_tx)

        # Dividends received by cooperative (optional)
        div_tx = DividendPayment.objects.filter(
            date__year=year, date__month=month
        )
        div_total = sum(d.amount for d in div_tx)

        total = interest_total + penalties_total + div_total

        # Export CSV
        if request.GET.get("export") == "csv":
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = f"attachment; filename=revenue_{month_str}.csv"
            writer = csv.writer(response)
            writer.writerow(["Source", "Amount"])
            writer.writerow(["Interest", interest_total])
            writer.writerow(["Penalties", penalties_total])
            writer.writerow(["Dividends", div_total])
            writer.writerow([])
            writer.writerow(["TOTAL", total])
            return response

        return render(
            request,
            "reports/monthly_revenue.html",
            {
                "interest": interest_total,
                "penalties": penalties_total,
                "dividends": div_total,
                "total": total,
                "month": month_str,
            },
        )


# =========================================================
# BANK STATEMENT IMPORT REPORT
# =========================================================

class BankStatementReportView(View):
    """
    URL: /reports/bank_statement/
    """

    def get(self, request):
        from cash_dividends.models import BankStatementLine

        rows = BankStatementLine.objects.all().order_by("-date")

        total = sum(r.amount for r in rows)

        # export
        if request.GET.get("export") == "csv":
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = "attachment; filename=bank_statement.csv"
            writer = csv.writer(response)
            writer.writerow(["Date", "Description", "Amount", "Balance"])
            for r in rows:
                writer.writerow([r.date, r.description, r.amount, r.balance])
            writer.writerow([])
            writer.writerow(["TOTAL", total])
            return response

        return render(
            request,
            "reports/bank_statement.html",
            {"rows": rows, "total": total},
        )


# =========================================================
# MONTHLY BANK RECONCILIATION
# =========================================================

class BankReconciliationView(View):
    """
    URL: /reports/bank_reconciliation/?month=2024-12
    """

    def get(self, request):

        from cash_dividends.models import BankStatementLine
        from savings.models import Transaction as SavingsTx

        month_str = request.GET.get("month")
        if not month_str:
            return HttpResponse("Missing ?month=YYYY-MM", status=400)

        year, month = map(int, month_str.split("-"))

        bank_lines = BankStatementLine.objects.filter(
            date__year=year, date__month=month
        )
        savings_tx = SavingsTx.objects.filter(
            date__year=year, date__month=month
        )

        bank_total = sum(b.amount for b in bank_lines)
        savings_total = sum(s.amount for s in savings_tx)

        difference = bank_total - savings_total

        return render(
            request,
            "reports/bank_reconciliation.html",
            {
                "bank_total": bank_total,
                "savings_total": savings_total,
                "difference": difference,
                "month": month_str,
            },
        )


# =========================================================
# INCOME & EXPENDITURE STATEMENT
# =========================================================

class IncomeExpenditureView(View):
    """
    URL: /reports/income_expenditure/?year=2024
    """

    def get(self, request):

        from loans.models import LoanTransaction
        from cash_dividends.models import DividendPayment

        year = int(request.GET.get("year", date.today().year))

        income_interest = LoanTransaction.objects.filter(
            date__year=year, tx_type="interest"
        )
        income_penalties = LoanTransaction.objects.filter(
            date__year=year, tx_type="penalty"
        )
        income_dividends = DividendPayment.objects.filter(
            date__year=year
        )

        total_income = (
            sum(i.amount for i in income_interest)
            + sum(p.amount for p in income_penalties)
            + sum(d.amount for d in income_dividends)
        )

        # Expenses to be added when available
        total_expenses = 0

        return render(
            request,
            "reports/income_expenditure.html",
            {
                "interest": sum(i.amount for i in income_interest),
                "penalties": sum(p.amount for p in income_penalties),
                "dividends": sum(d.amount for d in income_dividends),
                "total_income": total_income,
                "total_expenses": total_expenses,
                "net": total_income - total_expenses,
                "year": year,
            },
        )


# =========================================================
# STATEMENT OF FINANCIAL POSITION (BALANCE SHEET)
# =========================================================

class FinancialPositionView(View):
    """
    URL: /reports/financial_position/?year=2024
    """

    def get(self, request):

        from savings.models import Transaction as SavingsTx
        from loans.models import LoanTransaction

        year = int(request.GET.get("year", date.today().year))

        # Assets: loans outstanding + bank + savings pool
        loans_outstanding = LoanTransaction.objects.filter(
            date__year__lte=year,
            tx_type="balance"
        ).aggregate(total=models.Sum("amount"))["total"] or 0

        savings_total = SavingsTx.objects.filter(
            date__year__lte=year
        ).aggregate(total=models.Sum("amount"))["total"] or 0

        assets = loans_outstanding + savings_total

        # Liabilities (none unless explicitly modeled)
        liabilities = 0

        equity = assets - liabilities

        return render(
            request,
            "reports/financial_position.html",
            {
                "assets": assets,
                "liabilities": liabilities,
                "equity": equity,
                "year": year,
            },
        )


# =========================================================
# AUDIT REPORT VIEW
# =========================================================

class AuditReportView(View):
    """
    URL: /reports/audit/
    """

    def get(self, request):
        return render(request, "reports/audit_report.html")

# =========================================================
# "AS AT" SYSTEM-WIDE REPORT
# =========================================================

class AsAtReportView(View):
    """
    URL: /reports/as_at_report/?date=YYYY-MM-DD
    Produces:
        - Savings totals per category
        - Loan totals per category
        - Net balances per account
        - Chart-friendly summary
    """

    def get(self, request):
        from savings.models import Account, Transaction as SavingsTx
        from loans.models import Loan, LoanTransaction
        from cash_dividends.models import DividendPayment

        date_str = request.GET.get("date")
        if date_str:
            try:
                as_at = datetime.strptime(date_str, "%Y-%m-%d").date()
            except:
                as_at = date.today()
        else:
            as_at = date.today()

        accounts = AccountProfile.objects.all()

        # Initialize totals
        summary = {
            "total_accounts": accounts.count(),
            "total_savings": 0,
            "total_loans": 0,
            "net_position": 0,
        }

        savings_totals = {
            "total_premium": 0,
            "fixed_target_deposits": 0,
            "shares_investment": 0,
        }

        loan_totals = {cat: 0 for cat in LOAN_CATEGORIES.keys()}

        # Rows for table
        rows = []

        for account in accounts:
            report = build_account_report(account, as_at)
            cache_report(account, report)

            # Aggregate summary
            account_savings = sum(report["savings"].values())
            account_loans = report["loans"]["total_loan_balance"]
            account_net = report["net_balance"]

            summary["total_savings"] += account_savings
            summary["total_loans"] += account_loans
            summary["net_position"] += account_net

            # Aggregate savings per category
            for key in savings_totals.keys():
                savings_totals[key] += report["savings"].get(key, 0)

            # Aggregate loans per category
            for key in LOAN_CATEGORIES.keys():
                loan_totals[key] += report["loans"].get(key, 0)

            rows.append({
                "account": account,
                "savings": report["savings"],
                "loans": report["loans"],
                "net_balance": account_net,
            })

        # Handle export CSV/JSON
        export_response = handle_export(request, {
            "as_at": as_at.isoformat(),
            "summary": summary,
            "savings_totals": savings_totals,
            "loan_totals": loan_totals,
            "rows": rows,
        }, filename=f"as_at_report_{as_at.isoformat()}")
        if export_response:
            return export_response

        return render(request, "reports/as_at.html", {
            "as_at": as_at,
            "summary": summary,
            "savings_totals": savings_totals,
            "loan_totals": loan_totals,
            "rows": rows,
        })

