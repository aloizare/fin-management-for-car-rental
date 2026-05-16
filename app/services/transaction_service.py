import csv
import io
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from statistics import mean, stdev
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from sklearn.linear_model import LinearRegression
import numpy as np
from app.services.data_preparation_service import prepare_transaction_data
from app.db import models
from app import schemas
from app.services.data_preparation_service import prepare_transaction_data

def predict_next_month_income(db: Session, organization_id: str):
    data = prepare_transaction_data(organization_id=organization_id, db=db)
    monthly = data["monthly"]

    if not monthly:
        return {"error": "No transaction data found","predict_available" : False}

    months = sorted(monthly.keys())

    income_data = []
    for key in months:
        total_income = float(monthly[key]["total_income"])
        if total_income < 0 or total_income > 1_000_000_000_000:
            continue
        income_data.append({"month": key, "income": total_income})

    if len(income_data) < 2:
        return {"error": "Not enough valid data to predict"}

    incomes = [item["income"] for item in income_data]

    # ✅ Filter outlier dengan Z-score sebelum prediksi
    if len(incomes) >= 3:
        avg = mean(incomes)
        sd = stdev(incomes)
        if sd > 0:
            incomes_filtered = [
                v for v in incomes
                if abs((v - avg) / sd) < 2.5  # buang yang > 2.5 std dev
            ]
            if len(incomes_filtered) >= 2:
                incomes = incomes_filtered

    # ✅ Cek apakah data kontinu (max gap 2 bulan)
    from datetime import datetime
    months_list = [item["month"] for item in income_data]
    gaps = []
    for i in range(1, len(months_list)):
        d1 = datetime.strptime(months_list[i-1], "%Y-%m")
        d2 = datetime.strptime(months_list[i], "%Y-%m")
        gap = (d2.year - d1.year) * 12 + (d2.month - d1.month)
        gaps.append(gap)

    has_large_gap = any(g > 2 for g in gaps)

    # ✅ Gunakan Linear Regression jika data cukup & kontinu
    method = "moving_average_last_3_months"
    if len(incomes) >= 4 and not has_large_gap:
        X = np.array(range(len(incomes))).reshape(-1, 1)
        y = np.array(incomes)
        model = LinearRegression().fit(X, y)
        predicted_income = float(model.predict([[len(incomes)]])[0])
        method = "linear_regression"
    else:
        # Fallback: moving average 3 bulan terakhir
        recent = incomes[-3:]
        predicted_income = mean(recent)
        if has_large_gap:
            method = "moving_average_fallback_gap_detected"

    predicted_income = max(0, predicted_income)  # income tidak boleh negatif

    last_income = incomes[-1]
    percentage_change = (
        ((predicted_income - last_income) / last_income) * 100
        if last_income != 0 else 0
    )

    # Hitung next month
    last_month_str = income_data[-1]["month"]
    last_date = datetime.strptime(last_month_str, "%Y-%m")
    if last_date.month == 12:
        next_month = f"{last_date.year + 1}-01"
    else:
        next_month = f"{last_date.year}-{last_date.month + 1:02d}"

    return {
        "months": [item["month"] for item in income_data],
        "income_per_month": incomes,
        "next_month": next_month,
        "predicted_next_month_income": round(predicted_income, 2),
        "trend_up": bool(predicted_income > last_income),
        "percentage_change": round(percentage_change, 2),
        "predict_available" : True
    }

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
        transaction_date = datetime.strptime(raw_date, "%d-%m-%Y").date()
        if transaction_date > date.today():
            errors.append(f"Baris {row_num}: transaction_date tidak boleh lebih dari hari ini")
    except ValueError:
        errors.append(f"Baris {row_num}: transaction_date tidak valid (format: DD-MM-YYYY)")
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

def create_transaction(
    db: Session,
    tx_data: schemas.TransactionCreate,
    organization_id: str
) -> models.Transaction:
    org = db.query(models.Organization).filter(models.Organization.id == organization_id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisasi tidak ditemukan")

    # Validasi ulang (defensive, walau sudah divalidasi Pydantic)
    if tx_data.amount is None or tx_data.amount <= 0:
        raise HTTPException(status_code=422, detail="Jumlah transaksi harus positif")
    if tx_data.category not in ("in", "out"):
        raise HTTPException(status_code=422, detail="Pilih kategori pemasukan atau pengeluaran")
    try:
        trx_date = datetime.strptime(tx_data.transaction_date, "%Y-%m-%d").date()
    except Exception:
        raise HTTPException(status_code=422, detail="Format tanggal tidak valid, gunakan YYYY-MM-DD")
    if trx_date > date.today():
        raise HTTPException(status_code=422, detail="Tanggal tidak boleh lebih besar dari hari ini")

    db_transaction = models.Transaction(
        amount=tx_data.amount,
        category=models.TransactionCategory(tx_data.category),
        transaction_date=trx_date,
        note=tx_data.note,
        organization_id=organization_id,
    )
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    return db_transaction

def get_paginated_transactions(
    db: Session,
    organization_id: str,
    page: int = 1,
    limit: int = 10
):
    skip = (page - 1) * limit
    query = db.query(models.Transaction).filter(
        models.Transaction.organization_id == organization_id,
        models.Transaction.deleted_at == None
    )
    total = query.count()
    transactions = query.order_by(models.Transaction.transaction_date.desc()).offset(skip).limit(limit).all()
    return transactions, total

def _get_owned_transaction(
    db: Session,
    organization_id: str,
    transaction_id:str,
) -> models.Transaction:
    transaction = (
        db.query(models.Transaction)
        .filter(
            models.Transaction.id == transaction_id,
            models.Transaction.organization_id == organization_id,
            models.Transaction.deleted_at == None,
        )
        .first()
    )
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaksi tidak ditemukan",
        )
    return transaction

def update_transaction(
    db: Session,
    transaction_id: str,
    transaction_data: schemas.TransactionUpdate,
    organization_id: str,
) -> models.Transaction:
    transaction = _get_owned_transaction(
        db=db,
        organization_id=organization_id,
        transaction_id=transaction_id,
    )

    payload = transaction_data.model_dump(exclude_unset=True)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tidak ada data yang diubah"
        )
    

    if "amount" in payload:
        if payload["amount"] is None or payload["amount"] <= 0:
            raise HTTPException(status_code=422, detail="Jumlah transaksi harus positif")
        transaction.amount = payload["amount"]

    if "category" in payload:
        if payload["category"] not in ("in", "out"):
            raise HTTPException(status_code=422, detail="Pilih kategori pemasukan atau pengeluaran")
        transaction.category = models.TransactionCategory(payload["category"])

    if "transaction_date" in payload:
        trx_date = payload["transaction_date"]
        if isinstance(trx_date, str):
            try:
                trx_date = datetime.strptime(trx_date, "%Y-%m-%d").date()
            except Exception:
                raise HTTPException(status_code=422, detail="Format tanggal tidak valid, gunakan YYYY-MM-DD")
        if trx_date > date.today():
            raise HTTPException(status_code=422, detail="Tanggal tidak boleh lebih besar dari hari ini")
        transaction.transaction_date = trx_date

    if "note" in payload:
        transaction.note = payload["note"]

    db.commit()
    db.refresh(transaction)
    return transaction

def soft_delete_transaction(
    db: Session,
    transaction_id: str,
    organization_id: str,
) -> dict:
    transaction = _get_owned_transaction(
        db=db,
        organization_id=organization_id,
        transaction_id=transaction_id,
    )

    transaction.deleted_at = datetime.utcnow()
    db.commit()

    return {
        "message": "Transaksi berhasil dihapus",
        "deleted_at": transaction.deleted_at,
    }

def get_monthly_profit_report(db, organization_id, start_date=None, end_date=None):
    data = prepare_transaction_data(
        organization_id=organization_id,
        db=db,
        start_date=start_date,
        end_date=end_date
    )

    items = []
    for _, value in data["monthly"].items():
        items.append({
            "month": value["month"],
            "year": value["year"],
            "month_number": value["month_number"],
            "total_income": float(value["total_income"]),
            "total_expense": float(value["total_expense"]),
            "profit": float(value["profit"]),
        })

    return {
        "items": items,
        "total_income": float(data["total_income"]),
        "total_expense": float(data["total_expense"]),
        "profit": float(data["profit"]),
    }