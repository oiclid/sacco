from django.urls import path
from . import views

app_name = "reports"

urlpatterns = [
    # -----------------------------
    # CASHBOOK, BANK & PAYMENT REPORTS
    # -----------------------------
    path("cashbook/", views.CashbookReportView.as_view(), name="cashbook"),
    path("monthly-repayments/", views.MonthlyRepaymentsView.as_view(), name="monthly_repayments"),
    path("monthly-disbursements/", views.MonthlyDisbursementsView.as_view(), name="monthly_disbursements"),
    path("monthly-revenue/", views.MonthlyRevenueView.as_view(), name="monthly_revenue"),
    path("bank-statements/", views.BankStatementReportView.as_view(), name="bank_statements"),
    path("bank-mandate/", views.BankMandateReportView.as_view(), name="bank_mandate"),
    path("bank-reconciliation/", views.BankReconciliationView.as_view(), name="bank_reconciliation"),
    path("bank-charges/", views.BankChargesReportView.as_view(), name="bank_charges"),

    # -----------------------------
    # ACCOUNT FINANCIALS
    # -----------------------------
    path("accounts-ledger/<int:account_id>/", views.AccountLedgerView.as_view(), name="accounts_ledger"),

    # -----------------------------
    # MAIN FINANCIAL STATEMENTS
    # -----------------------------
    path("income-expenditure/", views.IncomeExpenditureView.as_view(), name="income_expenditure"),
    path("statement-financial-position/", views.FinancialPositionView.as_view(), name="financial_position"),

    # -----------------------------
    # AUDIT REPORT
    # -----------------------------
    path("audit-report/", views.AuditReportView.as_view(), name="audit_report"),

    # -----------------------------
    # MASTER ACCOUNT SUMMARY REPORT
    # -----------------------------
    path("summary/", views.AsAtSummaryView.as_view(), name="financial_summary"),

    # -----------------------------
    # DASHBOARD
    # -----------------------------
    path("dashboard/", views.ReportsDashboardView.as_view(), name="dashboard"),
    path("as_at_report/", views.AsAtReportView.as_view(), name="as_at_report"),
]
