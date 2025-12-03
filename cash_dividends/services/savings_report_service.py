import csv
import io
from django.http import HttpResponse
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from .models import SavingsAccount, Transaction

# -----------------------------
# Queryset Generation
# -----------------------------
def generate_savings_report_queryset(account_type=None, transaction_type=None):
    """
    Return filtered querysets for accounts and transactions.
    """
    accounts = SavingsAccount.objects.all()
    transactions = Transaction.objects.select_related('account', 'related_account')

    if account_type:
        accounts = accounts.filter(account_type=account_type)
        transactions = transactions.filter(account__account_type=account_type)

    if transaction_type:
        transactions = transactions.filter(transaction_type=transaction_type)

    return accounts.order_by('-created_at'), transactions.order_by('-date')


# -----------------------------
# CSV Export
# -----------------------------
def export_savings_csv(accounts, transactions):
    # Accounts CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="savings_report.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "User", "Account Type", "Balance",
        "Total Dividends", "Total Withdrawals", "Total Charges", "Created At"
    ])
    for acc in accounts:
        writer.writerow([
            acc.user.username,
            acc.account_type,
            f"{acc.balance:.2f}",
            f"{acc.total_dividends:.2f}",
            f"{acc.total_withdrawals:.2f}",
            f"{acc.total_charges:.2f}",
            acc.created_at
        ])

    writer.writerow([])  # empty row
    writer.writerow(["Transactions"])
    writer.writerow([
        "Account", "Transaction Type", "Amount", "Date", "Related Account", "Description"
    ])
    for t in transactions:
        writer.writerow([
            f"{t.account.user.username} - {t.account.account_type}",
            t.transaction_type,
            f"{t.amount:.2f}",
            t.date,
            t.related_account or "",
            t.description or ""
        ])

    return response


# -----------------------------
# XLSX Export
# -----------------------------
def export_savings_xlsx(accounts, transactions):
    output = io.BytesIO()
    wb = Workbook()
    ws_acc = wb.active
    ws_acc.title = "Accounts"

    # Accounts sheet
    ws_acc.append([
        "User", "Account Type", "Balance",
        "Total Dividends", "Total Withdrawals", "Total Charges", "Created At"
    ])
    for acc in accounts:
        ws_acc.append([
            acc.user.username,
            acc.account_type,
            float(acc.balance),
            float(acc.total_dividends),
            float(acc.total_withdrawals),
            float(acc.total_charges),
            acc.created_at.strftime("%Y-%m-%d %H:%M")
        ])

    # Transactions sheet
    ws_tx = wb.create_sheet(title="Transactions")
    ws_tx.append([
        "Account", "Transaction Type", "Amount", "Date", "Related Account", "Description"
    ])
    for t in transactions:
        ws_tx.append([
            f"{t.account.user.username} - {t.account.account_type}",
            t.transaction_type,
            float(t.amount),
            t.date.strftime("%Y-%m-%d"),
            str(t.related_account) if t.related_account else "",
            t.description or ""
        ])

    wb.save(output)
    output.seek(0)

    response = HttpResponse(
        output,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response['Content-Disposition'] = 'attachment; filename="savings_report.xlsx"'
    return response


# -----------------------------
# PDF Export
# -----------------------------
def export_savings_pdf(accounts, transactions):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="savings_report.pdf"'

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    # Accounts header
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Accounts")
    y -= 25
    c.setFont("Helvetica", 10)
    for acc in accounts:
        line = f"{acc.user.username} | {acc.account_type} | Balance: ₦{acc.balance:.2f} | Dividends: ₦{acc.total_dividends:.2f} | Withdrawals: ₦{acc.total_withdrawals:.2f} | Charges: ₦{acc.total_charges:.2f}"
        c.drawString(50, y, line)
        y -= 15
        if y < 50:  # new page
            c.showPage()
            y = height - 50

    # Transactions header
    y -= 25
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Transactions")
    y -= 25
    c.setFont("Helvetica", 10)
    for t in transactions:
        line = f"{t.account.user.username} - {t.account.account_type} | {t.transaction_type} | ₦{t.amount:.2f} | {t.date} | {t.related_account or ''} | {t.description or ''}"
        c.drawString(50, y, line)
        y -= 15
        if y < 50:
            c.showPage()
            y = height - 50

    c.save()
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response
