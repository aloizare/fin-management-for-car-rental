from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import models
from app.db.database import get_db
from app.routers.auth import authenticated_user
from app import schemas
from app.services.vehicle_service import (
    create_vehicle,
    get_paginated_vehicles,
    get_vehicle_by_id,
    update_vehicle,
    delete_vehicle,
)

router = APIRouter(prefix="/vehicles", tags=["Vehicle"])


@router.post("", response_model=schemas.VehicleResponse, status_code=201)
def create_new_vehicle(
    data: schemas.VehicleCreate,
    current_user: models.User = Depends(authenticated_user),
    db: Session = Depends(get_db),
):
    return create_vehicle(db=db, data=data, organization_id=str(current_user.organization_id))


@router.get("", response_model=schemas.PaginatedVehicleResponse)
def list_vehicles(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter status: aktif / tidak_aktif / dalam_perawatan"),
    current_user: models.User = Depends(authenticated_user),
    db: Session = Depends(get_db),
):
    items, total = get_paginated_vehicles(
        db=db,
        organization_id=str(current_user.organization_id),
        page=page,
        limit=limit,
        status_filter=status,
    )
    return {"items": items, "total": total, "page": page, "limit": limit}


@router.get("/{vehicle_id}", response_model=schemas.VehicleResponse)
def get_vehicle(
    vehicle_id: UUID,
    current_user: models.User = Depends(authenticated_user),
    db: Session = Depends(get_db),
):
    return get_vehicle_by_id(db=db, vehicle_id=str(vehicle_id), organization_id=str(current_user.organization_id))


@router.patch("/{vehicle_id}", response_model=schemas.VehicleResponse)
def update_vehicle_by_id(
    vehicle_id: UUID,
    data: schemas.VehicleUpdate,
    current_user: models.User = Depends(authenticated_user),
    db: Session = Depends(get_db),
):
    return update_vehicle(
        db=db,
        vehicle_id=str(vehicle_id),
        data=data,
        organization_id=str(current_user.organization_id),
    )


@router.delete("/{vehicle_id}", response_model=schemas.VehicleDeleteResponse)
def delete_vehicle_by_id(
    vehicle_id: UUID,
    current_user: models.User = Depends(authenticated_user),
    db: Session = Depends(get_db),
):
    return delete_vehicle(db=db, vehicle_id=str(vehicle_id), organization_id=str(current_user.organization_id))
