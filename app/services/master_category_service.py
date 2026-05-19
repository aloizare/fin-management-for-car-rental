from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import TransactionCategoryMaster
from app.db.seeds import seed_default_categories
from app import schemas


def _ensure_seeded(db: Session, organization_id: str):
    count = db.query(TransactionCategoryMaster).filter(
        TransactionCategoryMaster.organization_id == organization_id,
        TransactionCategoryMaster.deleted_at.is_(None),
    ).count()
    if count == 0:
        seed_default_categories(db, organization_id)


def get_categories(db: Session, organization_id: str, type_filter: str | None = None):
    _ensure_seeded(db, organization_id)
    query = db.query(TransactionCategoryMaster).filter(
        TransactionCategoryMaster.organization_id == organization_id,
        TransactionCategoryMaster.deleted_at.is_(None),
    )
    if type_filter:
        query = query.filter(TransactionCategoryMaster.type == type_filter)
    return query.order_by(TransactionCategoryMaster.is_default.desc(), TransactionCategoryMaster.name).all()


def create_category(
    db: Session,
    data: schemas.TransactionCategoryMasterCreate,
    organization_id: str,
) -> TransactionCategoryMaster:
    existing = db.query(TransactionCategoryMaster).filter(
        TransactionCategoryMaster.organization_id == organization_id,
        TransactionCategoryMaster.name == data.name,
        TransactionCategoryMaster.type == data.type,
        TransactionCategoryMaster.deleted_at.is_(None),
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Kategori dengan nama dan tipe yang sama sudah ada",
        )

    category = TransactionCategoryMaster(
        name=data.name,
        type=data.type,
        is_default=False,
        organization_id=organization_id,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, category_id: str, organization_id: str) -> dict:
    category = db.query(TransactionCategoryMaster).filter(
        TransactionCategoryMaster.id == category_id,
        TransactionCategoryMaster.organization_id == organization_id,
        TransactionCategoryMaster.deleted_at.is_(None),
    ).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kategori tidak ditemukan")
    if category.is_default:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kategori default tidak bisa dihapus",
        )
    category.deleted_at = datetime.utcnow()
    db.commit()
    return {"message": "Kategori berhasil dihapus", "deleted_at": category.deleted_at}
