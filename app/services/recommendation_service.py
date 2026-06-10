import os
from openai import OpenAI
from sqlalchemy.orm import Session
from app.db import models
from app.services.data_preparation_service import prepare_transaction_data

def get_financial_recommendation(db: Session, organization_id: str, prediction_data: dict) -> str | None:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return None

    # Gather Context
    data = prepare_transaction_data(organization_id=organization_id, db=db)
    
    # Vehicle Context
    total_vehicles = db.query(models.Vehicle).filter(
        models.Vehicle.organization_id == organization_id, 
        models.Vehicle.deleted_at.is_(None)
    ).count()
    
    active_vehicles = db.query(models.Vehicle).filter(
        models.Vehicle.organization_id == organization_id, 
        models.Vehicle.deleted_at.is_(None), 
        models.Vehicle.status == models.VehicleStatus.AKTIF
    ).count()
    
    inactive_vehicles = db.query(models.Vehicle).filter(
        models.Vehicle.organization_id == organization_id, 
        models.Vehicle.deleted_at.is_(None), 
        models.Vehicle.status == models.VehicleStatus.TIDAK_AKTIF
    ).count()
    
    maintenance_vehicles = db.query(models.Vehicle).filter(
        models.Vehicle.organization_id == organization_id, 
        models.Vehicle.deleted_at.is_(None), 
        models.Vehicle.status == models.VehicleStatus.DALAM_PERAWATAN
    ).count()
    
    # Categories context
    categories_in = db.query(models.TransactionCategoryMaster).filter(
        models.TransactionCategoryMaster.organization_id == organization_id, 
        models.TransactionCategoryMaster.type == "in",
        models.TransactionCategoryMaster.deleted_at.is_(None)
    ).all()
    
    categories_out = db.query(models.TransactionCategoryMaster).filter(
        models.TransactionCategoryMaster.organization_id == organization_id, 
        models.TransactionCategoryMaster.type == "out",
        models.TransactionCategoryMaster.deleted_at.is_(None)
    ).all()

    # Format Monthly Summaries
    months = sorted(list(data["monthly"].keys()))[-3:] # Last 3 months
    monthly_summary = ""
    for m in months:
        m_data = data["monthly"][m]
        monthly_summary += f"- {m}: Pemasukan Rp {m_data['total_income']:,.0f}, Pengeluaran Rp {m_data['total_expense']:,.0f}, Profit Rp {m_data['profit']:,.0f}\n"

    prediction_income = prediction_data.get("predicted_next_month_income", 0)
    percentage_change = prediction_data.get("percentage_change", 0)
    trend = "naik" if prediction_data.get("trend_up") else "turun"

    prompt = f"""Kamu adalah konsultan keuangan untuk bisnis rental mobil.
Berdasarkan data berikut, berikan rekomendasi strategis.

[DATA KEUANGAN]
- Prediksi income bulan depan: Rp {prediction_income:,.0f} (tren: {trend} {percentage_change}%)
- Ringkasan Keuangan (3 bulan terakhir):
{monthly_summary}
- Kategori Pemasukan yang digunakan: {', '.join([c.name for c in categories_in])}
- Kategori Pengeluaran yang digunakan: {', '.join([c.name for c in categories_out])}

[DATA ARMADA]
- Total kendaraan: {total_vehicles}
- Aktif disewakan: {active_vehicles}
- Tidak aktif: {inactive_vehicles}
- Dalam perawatan: {maintenance_vehicles}

[INSTRUKSI]
Jika tren naik: Berikan 3-5 rekomendasi untuk memastikan prediksi tercapai atau memaksimalkan potensi.
Jika tren turun: Berikan 3-5 rekomendasi untuk bounce back dan mencegah penurunan profit.

Format output dalam bahasa Indonesia, singkat dan actionable.
Gunakan format Markdown (heading, bullet points, bold) agar bisa langsung di-render di frontend. Jangan gunakan HTML.
"""

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    model = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            timeout=15.0
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error getting AI recommendation: {e}")
        return None
