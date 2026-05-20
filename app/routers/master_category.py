from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import models
from app.db.database import get_db
from app.routers.auth import authenticated_user
from app import schemas
from app.services.master_category_service import (
    get_categories,
    create_category,
    delete_category,
)

router = APIRouter(prefix="/master-categories", tags=["Master Category"])


@router.get("", response_model=List[schemas.TransactionCategoryMasterResponse])
def list_categories(
    type: Optional[str] = Query(None, description="Filter tipe: in / out"),
    current_user: models.User = Depends(authenticated_user),
    db: Session = Depends(get_db),
):
    return get_categories(
        db=db,
        organization_id=str(current_user.organization_id),
        type_filter=type,
    )


@router.post("", response_model=schemas.TransactionCategoryMasterResponse, status_code=201)
def create_new_category(
    data: schemas.TransactionCategoryMasterCreate,
    current_user: models.User = Depends(authenticated_user),
    db: Session = Depends(get_db),
):
    return create_category(db=db, data=data, organization_id=str(current_user.organization_id))


@router.delete("/{category_id}")
def delete_category_by_id(
    category_id: UUID,
    current_user: models.User = Depends(authenticated_user),
    db: Session = Depends(get_db),
):
    return delete_category(db=db, category_id=str(category_id), organization_id=str(current_user.organization_id))
