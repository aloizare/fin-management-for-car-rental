from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db.models import Vehicle, VehicleStatus
from app import schemas


def create_vehicle(db: Session, data: schemas.VehicleCreate, organization_id: str) -> Vehicle:
    vehicle = Vehicle(
        plat_nomor=data.plat_nomor,
        merek=data.merek,
        model=data.model,
        tahun=data.tahun,
        tarif_sewa=data.tarif_sewa,
        status=VehicleStatus(data.status),
        organization_id=organization_id,
    )
    db.add(vehicle)
    try:
        db.commit()
        db.refresh(vehicle)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Plat nomor {data.plat_nomor} sudah terdaftar di organisasi ini",
        )
    return vehicle


def get_paginated_vehicles(
    db: Session,
    organization_id: str,
    page: int,
    limit: int,
    status_filter: str | None = None,
):
    query = db.query(Vehicle).filter(
        Vehicle.organization_id == organization_id,
        Vehicle.deleted_at.is_(None),
    )
    if status_filter:
        query = query.filter(Vehicle.status == VehicleStatus(status_filter))

    total = query.count()
    items = query.order_by(Vehicle.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    return items, total


def get_vehicle_by_id(db: Session, vehicle_id: str, organization_id: str) -> Vehicle:
    vehicle = db.query(Vehicle).filter(
        Vehicle.id == vehicle_id,
        Vehicle.organization_id == organization_id,
        Vehicle.deleted_at.is_(None),
    ).first()
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kendaraan tidak ditemukan")
    return vehicle


def update_vehicle(
    db: Session,
    vehicle_id: str,
    data: schemas.VehicleUpdate,
    organization_id: str,
) -> Vehicle:
    vehicle = get_vehicle_by_id(db, vehicle_id, organization_id)

    if data.merek is not None:
        vehicle.merek = data.merek
    if data.model is not None:
        vehicle.model = data.model
    if data.tahun is not None:
        vehicle.tahun = data.tahun
    if data.tarif_sewa is not None:
        vehicle.tarif_sewa = data.tarif_sewa
    if data.status is not None:
        vehicle.status = VehicleStatus(data.status)

    vehicle.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(vehicle)
    return vehicle


def delete_vehicle(db: Session, vehicle_id: str, organization_id: str) -> dict:
    vehicle = get_vehicle_by_id(db, vehicle_id, organization_id)
    vehicle.deleted_at = datetime.utcnow()
    db.commit()
    return {"message": "Kendaraan berhasil dihapus", "deleted_at": vehicle.deleted_at}
