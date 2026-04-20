from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io

from app.db import models
from app.db.database import get_db
from app.routers.auth import authenticated_user
from app.services.transaction_service import bulk_upload_csv, export_csv, export_pdf

router = APIRouter(prefix="/transactions", tags=["Transaction"])


@router.post("/bulk-upload")
async def bulk_upload(
    file: UploadFile = File(...),
    current_user: models.User = Depends(authenticated_user),
    db: Session = Depends(get_db),
):
    return await bulk_upload_csv(
        file=file,
        organization_id=str(current_user.organization_id),
        db=db,
    )


@router.get("/export/csv")
def download_csv(
    start_date: Optional[date] = Query(None, description="Filter dari tanggal (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Filter sampai tanggal (YYYY-MM-DD)"),
    current_user: models.User = Depends(authenticated_user),
    db: Session = Depends(get_db),
):
    csv_bytes = export_csv(
        organization_id=str(current_user.organization_id),
        db=db,
        start_date=start_date,
        end_date=end_date,
    )
    filename = f"transaksi_{start_date or 'all'}_{end_date or 'all'}.csv"
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/export/pdf")
def download_pdf(
    start_date: Optional[date] = Query(None, description="Filter dari tanggal (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Filter sampai tanggal (YYYY-MM-DD)"),
    current_user: models.User = Depends(authenticated_user),
    db: Session = Depends(get_db),
):
    pdf_bytes = export_pdf(
        organization_id=str(current_user.organization_id),
        db=db,
        start_date=start_date,
        end_date=end_date,
    )
    filename = f"laporan_{start_date or 'all'}_{end_date or 'all'}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
