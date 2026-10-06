from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from app.database import get_db
from app.models import Issue
from app.auth import get_current_user


router = APIRouter(
    prefix="/api/v1/analytics",
    tags=["Analytics"]
)


@router.get("/quality-metrics")
def quality_metrics(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    total = db.query(Issue).count()

    resolved = db.query(Issue).filter(
        Issue.status.in_(["RESOLVED", "CLOSED"])
    ).count()

    fix_rate = (
        (resolved / total) * 100
        if total > 0 else 0
    )

    resolved_issues = db.query(Issue).filter(
        Issue.status.in_(["RESOLVED", "CLOSED"]),
        Issue.created_at.isnot(None),
        Issue.updated_at.isnot(None)
    ).all()

    resolution_times = []

    for issue in resolved_issues:

        if issue.created_at and issue.updated_at:

            hours = (
                issue.updated_at - issue.created_at
            ).total_seconds() / 3600

            resolution_times.append(hours)

    mttr = (
        sum(resolution_times) / len(resolution_times)
        if resolution_times else 0
    )

    production_bugs = db.query(Issue).filter(
        Issue.environment_details.ilike("%production%")
    ).count()

    leakage = (
        (production_bugs / total) * 100
        if total > 0 else 0
    )

    critical_open = db.query(Issue).filter(
        Issue.severity == "CRITICAL",
        Issue.status.notin_(["RESOLVED", "CLOSED"])
    ).count()

    open_issues = db.query(Issue).filter(
        Issue.status.notin_(["RESOLVED", "CLOSED"])
    ).count()

    backlog_health = 100

    backlog_health -= critical_open * 15

    if open_issues > 20:
        backlog_health -= 20
    elif open_issues > 10:
        backlog_health -= 10

    backlog_health = max(
        0,
        min(100, backlog_health)
    )

    return {
        "total_issues": total,
        "resolved_issues": resolved,
        "fix_rate": round(fix_rate, 2),
        "mttr_hours": round(mttr, 2),
        "production_bugs": production_bugs,
        "leakage": round(leakage, 2),
        "open_issues": open_issues,
        "critical_open": critical_open,
        "backlog_health": backlog_health
    }


@router.get("/defect-trends")
def defect_trends(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    today = datetime.utcnow().date()

    dates = []
    counts = []

    for i in range(13, -1, -1):

        day = today - timedelta(days=i)

        start = datetime.combine(
            day,
            datetime.min.time()
        )

        end = start + timedelta(days=1)

        count = db.query(Issue).filter(
            Issue.created_at >= start,
            Issue.created_at < end
        ).count()

        dates.append(
            day.strftime("%Y-%m-%d")
        )

        counts.append(count)

    return {
        "dates": dates,
        "counts": counts
    }


@router.get("/plotly-charts")
def plotly_charts(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    severity_rows = db.query(
        Issue.severity,
        func.count(Issue.id)
    ).group_by(
        Issue.severity
    ).all()

    severity = {}

    for level, count in severity_rows:
        severity[level or "UNKNOWN"] = count

    workflow_rows = db.query(
        Issue.status,
        func.count(Issue.id)
    ).group_by(
        Issue.status
    ).all()

    workflow = {}

    for status, count in workflow_rows:
        workflow[status or "UNKNOWN"] = count

    return {
        "severity": severity,
        "workflow": workflow
    }