import csv
import io
from django.http import HttpResponse
import xlsxwriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from django.utils import timezone
from loans.models import Loan

# ------------------------------
# Queryset generation / filtering
# ------------------------------
def generate_loan_report_queryset(user=None, loan_type=None, status=None):
    """
    Return queryset filtered by user, loan_type, and status.
    Automatically applies default checks on loans.
    """
    qs = Loan.objects.all()

    # Apply role-based filtering
    if user and not user.is_superadmin() and not user.is_admin():
        qs = qs.filter(user=user)

    # Filter by loan_type
    if loan_type:
        qs = qs.filter(loan_type=loan_type)

    # Filter by status
    if status:
        qs = qs.filter(status=status)

    # Check defaults for each loan
    for loan in qs:
        loan.check_default()

    return qs


# ------------------------------
# CSV Export
# ------------------------------
def export_loans_csv(queryset):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=loan_report.csv"
    writer = csv.writer(response)
    headers = [
        "ID", "User", "Loan Type", "Amount", "Interest Rate",
        "Term (Months)", "Status", "Total Repaid", "Outstanding", "Created At"
    ]
    writer.writerow(headers)
    for loan in queryset:
        writer.writerow([
            loan.pk,
            loan.user.username,
            loan.loan_type,
            float(loan.amount),
            float(loan.interest_rate),
            loan.term_months,
            loan.status,
            float(loan.total_repaid),
            float(loan.outstanding),
            loan.created_at,
        ])
    return response


# ------------------------------
# XLSX Export
# ------------------------------
def export_loans_xlsx(queryset):
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet("Loan Report")
    headers = [
        "ID", "User", "Loan Type", "Amount", "Interest Rate",
        "Term (Months)", "Status", "Total Repaid", "Outstanding", "Created At"
    ]
    for col, header in enumerate(headers):
        worksheet.write(0, col, header)
    for row, loan in enumerate(queryset, start=1):
        worksheet.write(row, 0, loan.pk)
        worksheet.write(row, 1, loan.user.username)
        worksheet.write(row, 2, loan.loan_type)
        worksheet.write(row, 3, float(loan.amount))
        worksheet.write(row, 4, float(loan.interest_rate))
        worksheet.write(row, 5, loan.term_months)
        worksheet.write(row, 6, loan.status)
        worksheet.write(row, 7, float(loan.total_repaid))
        worksheet.write(row, 8, float(loan.outstanding))
        worksheet.write(row, 9, str(loan.created_at))
    workbook.close()
    output.seek(0)
    response = HttpResponse(
        output.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = "attachment; filename=loan_report.xlsx"
    return response


# ------------------------------
# PDF Export
# ------------------------------
def export_loans_pdf(queryset):
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "attachment; filename=loan_report.pdf"
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    y = 750
    p.setFont("Helvetica", 10)
    p.drawString(30, y, f"Loan Report - Generated: {timezone.now().strftime('%Y-%m-%d %H:%M')}")
    y -= 30

    for loan in queryset:
        line = (
            f"Loan #{loan.pk} | User: {loan.user.username} | Type: {loan.loan_type} | "
            f"Amount: ₦{loan.amount:,.2f} | Rate: {loan.interest_rate}% | "
            f"Term: {loan.term_months} months | Status: {loan.status} | "
            f"Total Repaid: ₦{loan.total_repaid:,.2f} | Outstanding: ₦{loan.outstanding:,.2f}"
        )
        p.drawString(30, y, line)
        y -= 15
        if y < 50:
            p.showPage()
            y = 750
    p.save()
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response
