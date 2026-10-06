from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Issue, User, ActivityLog
from ..auth import get_current_user


router = APIRouter(
    prefix="/api/v1/comments",
    tags=["Comments"]
)


class CommentRequest(BaseModel):
    comment: str


@router.post("/{issue_id}")
def add_comment(
    issue_id: int,
    request: CommentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    issue = db.get(Issue, issue_id)

    if not issue:
        raise HTTPException(
            status_code=404,
            detail="Issue not found"
        )

    if not request.comment.strip():
        raise HTTPException(
            status_code=400,
            detail="Comment cannot be empty"
        )

    activity = ActivityLog(
        issue_id=issue_id,
        user_id=current_user.id,
        action="COMMENT_ADDED",
        details=request.comment,
        created_at=datetime.now(timezone.utc)
    )

    db.add(activity)
    db.commit()
    db.refresh(activity)

    return {
        "message": "Comment added successfully",
        "issue_id": issue_id,
        "comment": request.comment,
        "user_id": current_user.id
    }


@router.get("/{issue_id}")
def get_comments(
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

    comments = (
        db.query(ActivityLog)
        .filter(
            ActivityLog.issue_id == issue_id,
            ActivityLog.action == "COMMENT_ADDED"
        )
        .order_by(ActivityLog.created_at.asc())
        .all()
    )

    return [
        {
            "id": item.id,
            "issue_id": item.issue_id,
            "user_id": item.user_id,
            "comment": item.details,
            "created_at": item.created_at
        }
        for item in comments
    ]