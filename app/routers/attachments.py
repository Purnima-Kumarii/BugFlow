import os
import shutil
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Issue, ActivityLog, User
from ..auth import get_current_user


router = APIRouter(
    prefix="/api/v1/attachments",
    tags=["Attachments"]
)


UPLOAD_DIR = "app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/{issue_id}")
def upload_attachment(
    issue_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    issue = db.get(Issue, issue_id)

    if not issue:
        raise HTTPException(
            status_code=404,
            detail="Issue not found"
        )

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file selected"
        )

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    safe_filename = f"{issue.issue_key}_{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    activity = ActivityLog(
        issue_id=issue_id,
        user_id=current_user.id,
        action="ATTACHMENT_ADDED",
        details=safe_filename,
        created_at=datetime.now(timezone.utc)
    )

    db.add(activity)
    db.commit()

    return {
        "message": "Attachment uploaded successfully",
        "issue_id": issue_id,
        "filename": safe_filename,
        "uploaded_by": current_user.id
    }