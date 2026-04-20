import csv
import io
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from app.db import models

def _validate_row(row: dict, row_num: int) -> dict:
    errors = []

    try:
        amount = Decimal(str(row.get("amount", "")).strip())
        if amount <= 0:
            errors.append(f"Baris {row_num}: amount harus lebih dari 0")
    except InvalidOperation:
        errors.append(f"Baris {row_num}: amount tidak valid")
        amount = None

    category = str(row.get("category", "")).strip().lower()
    if category not in ("in", "out"):
        errors.append(f"Baris {row_num}: category harus 'in' atau 'out'")

    raw_date = str(row.get("transaction_date", "")).strip()
    try:
        transaction_date = date.fromisoformat(raw_date)
        if transaction_date > date.today():
            errors.append(f"Baris {row_num}: transaction_date tidak boleh lebih dari hari ini")
    except ValueError:
        errors.append(f"Baris {row_num}: transaction_date tidak valid (format: YYYY-MM-DD)")
        transaction_date = None

    # note opsional
    note = str(row.get("note", "")).strip() or None

    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=errors,
        )

    return {
        "amount": amount,
        "category": category,
        "transaction_date": transaction_date,
        "note": note,
    }

async def bulk_upload_csv(
    file: UploadFile,
    organization_id: str,
    db: Session,
) -> dict:
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File harus berformat CSV",
        )

    content = await file.read()

    try:
        decoded = content.decode("utf-8")
    except UnicodeDecodeError:
        decoded = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(decoded))

    required_columns = {"amount", "category", "transaction_date"}
    if not required_columns.issubset(set(reader.fieldnames or [])):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CSV harus memiliki kolom: {', '.join(required_columns)}. Kolom opsional: note",
        )

    rows = list(reader)
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File CSV kosong",
        )

    new_transactions = []
    for i, row in enumerate(rows, start=2):  # start=2 karena baris 1 adalah header
        validated = _validate_row(row, i)
        new_transactions.append(
            models.Transaction(
                amount=validated["amount"],
                category=models.TransactionCategory(validated["category"]),
                transaction_date=validated["transaction_date"],
                note=validated["note"],
                organization_id=organization_id,
            )
        )

    db.add_all(new_transactions)
    db.commit()

    return {
        "message": f"{len(new_transactions)} transaksi berhasil diimport",
        "total_imported": len(new_transactions),
    }

def export_csv(
    organization_id: str,
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> bytes:
    transactions = _get_transactions(organization_id, db, start_date, end_date)

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["id", "amount", "category", "transaction_date", "note", "created_at"])

    for trx in transactions:
        writer.writerow([
            str(trx.id),
            trx.amount,
            trx.category.value,
            trx.transaction_date,
            trx.note or "",
            trx.created_at,
        ])

    return output.getvalue().encode("utf-8")

def export_pdf(
    organization_id: str,
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> bytes:
    transactions = _get_transactions(organization_id, db, start_date, end_date)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Laporan Transaksi Keuangan", styles["Title"]))
    elements.append(Paragraph(
        f"Periode: {start_date or 'Semua'} s/d {end_date or 'Semua'}",
        styles["Normal"]
    ))
    elements.append(Spacer(1, 0.5*cm))

    total_in = sum(t.amount for t in transactions if t.category.value == "in")
    total_out = sum(t.amount for t in transactions if t.category.value == "out")
    profit = total_in - total_out

    summary_data = [
        ["Total Pemasukan", f"Rp {total_in:,.2f}"],
        ["Total Pengeluaran", f"Rp {total_out:,.2f}"],
        ["Profit", f"Rp {profit:,.2f}"],
    ]
    summary_table = Table(summary_data, colWidths=[8*cm, 8*cm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.lightblue),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.5*cm))

    table_data = [["No", "Tanggal", "Kategori", "Jumlah", "Keterangan"]]
    for i, trx in enumerate(transactions, start=1):
        table_data.append([
            i,
            str(trx.transaction_date),
            trx.category.value.upper(),
            f"Rp {trx.amount:,.2f}",
            trx.note or "-",
        ])

    if not transactions:
        table_data.append(["-", "-", "-", "-", "Tidak ada transaksi"])

    trx_table = Table(table_data, colWidths=[1*cm, 3.5*cm, 3*cm, 4*cm, 5.5*cm])
    trx_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ALIGN", (4, 1), (4, -1), "LEFT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightyellow]),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(trx_table)

    elements.append(Spacer(1, 0.5*cm))
    elements.append(Paragraph(
        f"Digenerate pada: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC",
        styles["Normal"]
    ))

    doc.build(elements)
    return buffer.getvalue()

def _get_transactions(
    organization_id: str,
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    query = (
        db.query(models.Transaction)
        .filter(
            models.Transaction.organization_id == organization_id,
            models.Transaction.deleted_at == None,
        )
    )
    if start_date:
        query = query.filter(models.Transaction.transaction_date >= start_date)
    if end_date:
        query = query.filter(models.Transaction.transaction_date <= end_date)

    return query.order_by(models.Transaction.transaction_date.desc()).all()
