from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Issue, ActivityLog, User
from ..auth import get_current_user


router = APIRouter(
    prefix="/api/v1/activity",
    tags=["Activity"]
)


@router.get("/{issue_id}")
def get_activity(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    issue = db.get(Issue, issue_id)

    if not issue:
        raise HTTPException(
            status_code=404,
            detail="Issue not found"
        )

    activities = (
        db.query(ActivityLog)
        .filter(ActivityLog.issue_id == issue_id)
        .order_by(ActivityLog.created_at.asc())
        .all()
    )

    return [
        {
            "id": activity.id,
            "issue_id": activity.issue_id,
            "user_id": activity.user_id,
            "action": activity.action,
            "details": activity.details,
            "created_at": activity.created_at
        }
        for activity in activities
    ]