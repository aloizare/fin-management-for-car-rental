
from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, case, desc
from app.db.database import get_db
from app.db.models import Transaction, TransactionCategory
from app.routers.auth import authenticated_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

def format_rupiah(value: int) -> str:
    return f"Rp{value:,.0f}".replace(",", ".")

def calc_trend(current: float, previous: float) -> dict:
    if previous == 0:
        return None
    pct = round((current - previous) / previous * 100, 1)
    is_positive = pct >= 0
    sign = "+" if is_positive else ""
    return {
        "percentage": abs(pct),
        "is_positive": is_positive,
        "text": f"{sign}{pct}% compared to last month"
    }

@router.get("")
def get_dashboard(
    db: Session = Depends(get_db),
    current_user=Depends(authenticated_user)
):
    year = 2026
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug"]
    month_numbers = [1, 2, 3, 4, 5, 6, 7, 8]

    totals = db.query(
        func.sum(case((Transaction.category == TransactionCategory.IN, Transaction.amount), else_=0)).label("total_revenue"),
        func.sum(case((Transaction.category == TransactionCategory.OUT, Transaction.amount), else_=0)).label("total_expenditure"),
    ).first()
    total_revenue = int(totals.total_revenue or 0)
    total_expenditure = int(totals.total_expenditure or 0)
    net_profit = total_revenue - total_expenditure

    monthly_rows = db.query(
        func.extract('month', Transaction.transaction_date).label('month'),
        func.sum(case((Transaction.category == TransactionCategory.IN, Transaction.amount), else_=0)).label('revenue'),
        func.sum(case((Transaction.category == TransactionCategory.OUT, Transaction.amount), else_=0)).label('expenditure'),
    ).filter(
        func.extract('year', Transaction.transaction_date) == year,
        func.extract('month', Transaction.transaction_date).between(1, 8),
    ).group_by('month').order_by('month').all()

    monthly_map = {int(row.month): row for row in monthly_rows}
    revenue_data = [int((monthly_map[m].revenue if m in monthly_map else 0) / 1_000_000_000) for m in month_numbers]
    expenditure_data = [int((monthly_map[m].expenditure if m in monthly_map else 0) / 1_000_000_000) for m in month_numbers]

    today = date.today()
    cur_m, prev_m = today.month, today.month - 1 if today.month > 1 else 12
    cur_row = monthly_map.get(cur_m)
    prev_row = monthly_map.get(prev_m)

    cur_rev = float(cur_row.revenue if cur_row else 0)
    prev_rev = float(prev_row.revenue if prev_row else 0)
    cur_exp = float(cur_row.expenditure if cur_row else 0)
    prev_exp = float(prev_row.expenditure if prev_row else 0)
    cur_profit = cur_rev - cur_exp
    prev_profit = prev_rev - prev_exp

    revenue_trend = calc_trend(cur_rev, prev_rev)
    expenditure_trend = calc_trend(cur_exp, prev_exp)
    net_profit_trend = calc_trend(cur_profit, prev_profit)

    acc = 0
    accumulated_profit_data = []
    for i in range(len(month_numbers)):
        acc += revenue_data[i] - expenditure_data[i]
        accumulated_profit_data.append(acc)

    amount_expr = func.sum(Transaction.amount)
    top_expenditures = db.query(
        Transaction.note.label("category"),
        amount_expr.label("value"),
        (amount_expr * 100.0 / func.sum(amount_expr).over()).label("percentage"),
    ).filter(
        Transaction.category == TransactionCategory.OUT,
        func.extract('year', Transaction.transaction_date) == year,
        func.extract('month', Transaction.transaction_date) == 4,
    ).group_by(Transaction.note).order_by(desc(amount_expr)).limit(5).all()

    expenditure_list = [
        {
            "category": row.category,
            "value": int(row.value),
            "percentage": round(float(row.percentage), 1),
        }
        for row in top_expenditures
    ]

    return {
        "data": {
            "summary_cards": {
                "total_revenue": {
                    "value": int(total_revenue),
                    "formatted_value": format_rupiah(int(total_revenue)),
                    "trend": revenue_trend
                },
                "total_expenditure": {
                    "value": int(total_expenditure),
                    "formatted_value": format_rupiah(int(total_expenditure)),
                    "trend": expenditure_trend
                },
                "net_profit": {
                    "value": int(net_profit),
                    "formatted_value": format_rupiah(int(net_profit)),
                    "trend": net_profit_trend
                }
            },
            "charts": {
                "revenue": {
                    "y_axis_unit": "Billion Rupiah",
                    "labels": months,
                    "dataset": {
                        "label": "Revenue",
                        "color_hex": "#4A72E8",
                        "data": revenue_data
                    }
                },
                "expenditure": {
                    "y_axis_unit": "Billion Rupiah",
                    "labels": months,
                    "dataset": {
                        "label": "Expenditure",
                        "color_hex": "#34C78B",
                        "data": expenditure_data
                    }
                },
                "accumulated_profit": {
                    "y_axis_unit": "Billion Rupiah",
                    "labels": months,
                    "dataset": {
                        "label": "Accumulated Profit",
                        "data": accumulated_profit_data
                    }
                },
                "expenditure_list": expenditure_list
            }
        }
    }
