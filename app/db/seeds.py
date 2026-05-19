from app.db.models import TransactionCategoryMaster

DEFAULT_CATEGORIES = [
    {"name": "Rental Mobil", "type": "in"},
    {"name": "Uang Muka Rental", "type": "in"},
    {"name": "Pemasukan lain-lain", "type": "in"},
    {"name": "BBM", "type": "out"},
    {"name": "Servis & Perawatan", "type": "out"},
    {"name": "Cuci Mobil", "type": "out"},
    {"name": "Asuransi", "type": "out"},
    {"name": "Gaji Supir", "type": "out"},
    {"name": "Parkir & Tol", "type": "out"},
    {"name": "Pengeluaran lain-lain", "type": "out"},
]


def seed_default_categories(db, organization_id: str):
    for cat in DEFAULT_CATEGORIES:
        db.add(TransactionCategoryMaster(
            name=cat["name"],
            type=cat["type"],
            is_default=True,
            organization_id=organization_id,
        ))
    db.commit()
