from datetime import date
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import extract

from app.db import models

def prepare_transaction_data(
    organization_id: str,
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> dict:
    query = db.query(models.Transaction).filter(
        models.Transaction.organization_id == organization_id,
        models.Transaction.deleted_at == None,
    )

    if start_date:
        query = query.filter(models.Transaction.transaction_date >= start_date)
    if end_date:
        query = query.filter(models.Transaction.transaction_date <= end_date)

    transactions = query.order_by(models.Transaction.transaction_date.asc()).all()

    monthly = {}
    grand_total_income = Decimal(0)
    grand_total_expense = Decimal(0)

    for t in transactions:
        key = f"{t.transaction_date.year}-{t.transaction_date.month:02d}"

        if key not in monthly:
            monthly[key] = {
                "month": key,
                "year": t.transaction_date.year,
                "month_number": t.transaction_date.month,
                "income": [],
                "expense": [],
                "total_income": Decimal(0),
                "total_expense": Decimal(0),
                "profit": Decimal(0),
            }

        if t.category.value == "in":
            monthly[key]["income"].append(_format_transaction(t))
            monthly[key]["total_income"] += t.amount
            grand_total_income += t.amount
        else:
            monthly[key]["expense"].append(_format_transaction(t))
            monthly[key]["total_expense"] += t.amount
            grand_total_expense += t.amount

    for key in monthly:
        monthly[key]["profit"] = monthly[key]["total_income"] - monthly[key]["total_expense"]

    return {
        "transactions": [_format_transaction(t) for t in transactions],
        "monthly": monthly,
        "total_income": grand_total_income,
        "total_expense": grand_total_expense,
        "profit": grand_total_income - grand_total_expense,
    }


def _format_transaction(t: models.Transaction) -> dict:
    return {
        "id": str(t.id),
        "amount": t.amount,
        "category": t.category.value,  # "in" atau "out"
        "transaction_date": t.transaction_date.isoformat(),
        "note": t.note or "",
        "organization_id": str(t.organization_id),
        "created_at": t.created_at.isoformat(),
    }