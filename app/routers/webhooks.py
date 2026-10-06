from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Issue, AuditLog
from app.auth import get_current_user


router = APIRouter(
    prefix="/api/v1/webhooks",
    tags=["Git Webhook"]
)

@router.post("/git")
async def git_webhook(
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    # GitHub/GitLab style commit message
    commit_message = ""

    if "head_commit" in payload:
        commit_message = payload["head_commit"].get(
            "message", ""
        )

    elif "commit" in payload:
        commit_message = payload["commit"].get(
            "message", ""
        )

    if not commit_message:
        commit_message = payload.get("message", "")

    if not commit_message:
        commit_message = payload.get("commit_message", "")

    # Find issue references such as:
    # fixes #2
    # closes #5
    # resolves #8
    import re

    matches = re.findall(
        r"\b(?:fixes|fixed|fix|closes|closed|close|resolves|resolved|resolve)\s+#(\d+)",
        commit_message,
        re.IGNORECASE
    )

    if not matches:
        return {
            "message": "No issue reference found",
            "updated_issues": []
        }

    updated_issues = []

    for issue_id in matches:

        issue = db.query(Issue).filter(
            Issue.id == int(issue_id)
        ).first()

        if not issue:
            continue

        old_status = issue.status

        # Move issue to QA verification
        issue.status = "QA_VERIFICATION"

        # Create audit log
        audit = AuditLog(
           issue_id=issue.id,
           user_id=current_user.id,
           action="STATUS_CHANGED",
           old_value=old_status,
           new_value="QA_VERIFICATION"
)

        db.add(audit)

        updated_issues.append({
            "issue_id": issue.id,
            "issue_key": issue.issue_key,
            "old_status": old_status,
            "new_status": "QA_VERIFICATION"
        })

    db.commit()

    return {
        "message": "Git webhook processed successfully",
        "commit_message": commit_message,
        "updated_issues": updated_issues
    }