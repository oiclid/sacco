import csv
import io
from decimal import Decimal
from django.utils import timezone
from django.http import HttpResponse
import xlsxwriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from loans.models import Loan, LoanRepayment


def generate_loan_report_queryset(user=None):
    """
    Return all loans or filter by user if provided.
    """
    qs = Loan.objects.all().order_by("-created_at")
    if user and not user.is_superadmin() and not user.is_admin():
        qs = qs.filter(user=user)
    return qs


def loan_report_summary(user=None):
    """
    Returns summary dictionary of loans, repayments, and defaults.
    """
    loans = generate_loan_report_queryset(user)
    total_loans = loans.count()
    total_amount = sum(l.amount for l in loans)
    total_repaid = sum(l.total_repaid for l in loans)
    total_outstanding = sum(l.outstanding for l in loans)
    defaulted_count = loans.filter(status="defaulted").count()
    
    return {
        "total_loans": total_loans,
        "total_amount": total_amount,
        "total_repaid": total_repaid,
        "total_outstanding": total_outstanding,
        "defaulted_count": defaulted_count,
        "loans": loans,
    }


# -----------------------------
# Export Functions
# -----------------------------

def export_loans_csv(loans_queryset):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=loan_report.csv"

    writer = csv.writer(response)
    writer.writerow([
        "ID", "User", "Loan Type", "Amount", "Interest Rate", "Term (Months)", 
        "Status", "Disbursed At", "Created At", "Total Repaid", "Outstanding"
    ])
    for loan in loans_queryset:
        writer.writerow([
            loan.pk,
            loan.user.username,
            loan.loan_type,
            float(loan.amount),
            float(loan.interest_rate),
            loan.term_months,
            loan.status,
            loan.disbursed_at or "",
            loan.created_at,
            float(loan.total_repaid),
            float(loan.outstanding)
        ])
    return response


def export_loans_xlsx(loans_queryset):
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet("Loans")
    headers = [
        "ID", "User", "Loan Type", "Amount", "Interest Rate", "Term (Months)", 
        "Status", "Disbursed At", "Created At", "Total Repaid", "Outstanding"
    ]
    for col, header in enumerate(headers):
        worksheet.write(0, col, header)

    for row, loan in enumerate(loans_queryset, start=1):
        worksheet.write(row, 0, loan.pk)
        worksheet.write(row, 1, loan.user.username)
        worksheet.write(row, 2, loan.loan_type)
        worksheet.write(row, 3, float(loan.amount))
        worksheet.write(row, 4, float(loan.interest_rate))
        worksheet.write(row, 5, loan.term_months)
        worksheet.write(row, 6, loan.status)
        worksheet.write(row, 7, str(loan.disbursed_at or ""))
        worksheet.write(row, 8, str(loan.created_at))
        worksheet.write(row, 9, float(loan.total_repaid))
        worksheet.write(row, 10, float(loan.outstanding))

    workbook.close()
    output.seek(0)
    response = HttpResponse(
        output.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = "attachment; filename=loan_report.xlsx"
    return response


def export_loans_pdf(loans_queryset):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 50
    p.setFont("Helvetica", 10)
    p.drawString(30, y, f"Loan Report - Generated: {timezone.now().strftime('%Y-%m-%d %H:%M')}")
    y -= 30

    for loan in loans_queryset:
        line = (
            f"Loan #{loan.pk} | User: {loan.user.username} | Type: {loan.loan_type} "
            f"| Amount: ₦{loan.amount:,.2f} | Rate: {loan.interest_rate}% | "
            f"Term: {loan.term_months} months | Status: {loan.status} | "
            f"Repaid: ₦{loan.total_repaid:,.2f} | Outstanding: ₦{loan.outstanding:,.2f}"
        )
        p.drawString(30, y, line)
        y -= 15
        if y < 50:
            p.showPage()
            y = height - 50
    p.save()
    pdf = buffer.getvalue()
    buffer.close()
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = "attachment; filename=loan_report.pdf"
    return response
