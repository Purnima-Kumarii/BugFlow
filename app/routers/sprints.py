from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Sprint, Project, User, Issue
from ..auth import get_current_user

router = APIRouter(
    prefix="/api/v1/sprints",
    tags=["Sprints"]
)


# =========================
# CREATE SPRINT
# =========================

@router.post("/")
def create_sprint(
    name: str,
    project_id: int,
    goal: str = "",
    start_date: str | None = None,
    end_date: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    project = db.get(Project, project_id)

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found"
        )

    sprint = Sprint(
        name=name,
        project_id=project_id,
        goal=goal,
        start_date=datetime.fromisoformat(start_date) if start_date else None,
        end_date=datetime.fromisoformat(end_date) if end_date else None,
        status="PLANNED"
    )

    db.add(sprint)
    db.commit()
    db.refresh(sprint)

    return {
        "message": "Sprint created successfully",
        "sprint_id": sprint.id,
        "name": sprint.name,
        "project_id": sprint.project_id,
        "goal": sprint.goal,
        "start_date": sprint.start_date,
        "end_date": sprint.end_date,
        "status": sprint.status
    }


# =========================
# GET SPRINTS
# =========================

@router.get("/")
def get_sprints(
    project_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    query = db.query(Sprint)

    if project_id:
        query = query.filter(
            Sprint.project_id == project_id
        )

    sprints = query.order_by(
        Sprint.id.desc()
    ).all()

    result = []

    for sprint in sprints:

        total = db.query(Issue).filter(
            Issue.sprint_id == sprint.id
        ).count()

        completed = db.query(Issue).filter(
            Issue.sprint_id == sprint.id,
            Issue.status == "CLOSED"
        ).count()

        result.append({
            "id": sprint.id,
            "name": sprint.name,
            "project_id": sprint.project_id,
            "goal": sprint.goal,
            "start_date": sprint.start_date,
            "end_date": sprint.end_date,
            "status": sprint.status,
            "total_issues": total,
            "completed_issues": completed
        })

    return result


# =========================
# UPDATE SPRINT STATUS
# =========================

@router.patch("/{sprint_id}/status")
def update_sprint_status(
    sprint_id: int,
    status: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    allowed_statuses = [
        "PLANNED",
        "ACTIVE",
        "COMPLETED"
    ]

    if status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail="Invalid sprint status"
        )

    sprint = db.get(Sprint, sprint_id)

    if not sprint:
        raise HTTPException(
            status_code=404,
            detail="Sprint not found"
        )

    sprint.status = status

    db.commit()
    db.refresh(sprint)

    return {
        "message": "Sprint status updated successfully",
        "sprint_id": sprint.id,
        "status": sprint.status
    }


# =========================
# ASSIGN ISSUE TO SPRINT
# =========================

@router.patch("/{sprint_id}/issues/{issue_id}")
def assign_issue_to_sprint(
    sprint_id: int,
    issue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    sprint = db.get(Sprint, sprint_id)

    if not sprint:
        raise HTTPException(
            status_code=404,
            detail="Sprint not found"
        )

    issue = db.get(Issue, issue_id)

    if not issue:
        raise HTTPException(
            status_code=404,
            detail="Issue not found"
        )

    if issue.project_id != sprint.project_id:
        raise HTTPException(
            status_code=400,
            detail="Issue and sprint belong to different projects"
        )

    issue.sprint_id = sprint_id

    db.commit()
    db.refresh(issue)

    return {
        "message": "Issue assigned to sprint successfully",
        "issue_id": issue.id,
        "issue_key": issue.issue_key,
        "sprint_id": sprint.id,
        "sprint_name": sprint.name
    }


# =========================
# SPRINT ISSUES
# =========================

@router.get("/{sprint_id}/issues")
def get_sprint_issues(
    sprint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    sprint = db.get(Sprint, sprint_id)

    if not sprint:
        raise HTTPException(
            status_code=404,
            detail="Sprint not found"
        )

    issues = db.query(Issue).filter(
        Issue.sprint_id == sprint_id
    ).order_by(
        Issue.created_at.desc()
    ).all()

    return [
        {
            "id": issue.id,
            "issue_key": issue.issue_key,
            "title": issue.title,
            "severity": issue.severity,
            "priority": issue.priority,
            "status": issue.status
        }
        for issue in issues
    ]


# =========================
# BACKLOG
# =========================

@router.get("/backlog/{project_id}")
def get_backlog(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    project = db.get(Project, project_id)

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found"
        )

    issues = db.query(Issue).filter(
        Issue.project_id == project_id,
        Issue.sprint_id.is_(None)
    ).order_by(
        Issue.created_at.desc()
    ).all()

    return [
        {
            "id": issue.id,
            "issue_key": issue.issue_key,
            "title": issue.title,
            "severity": issue.severity,
            "priority": issue.priority,
            "status": issue.status,
            "sprint_id": issue.sprint_id
        }
        for issue in issues
    ]