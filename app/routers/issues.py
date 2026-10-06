from pydantic import BaseModel
from difflib import SequenceMatcher
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    Issue,
    User,
    Project,
    BugCategory,
    AuditLog,
    IssueStatus,
    Severity,
    Priority,
    Tag, issue_tags,
)
from ..auth import get_current_user, require_roles, UserRole


router = APIRouter(
    prefix="/api/v1/issues",
    tags=["Issues"]
)


# --------------------------------------------------
# DUPLICATE SIMILARITY
# --------------------------------------------------

def calculate_similarity(title1: str, title2: str) -> float:
    return SequenceMatcher(
        None,
        title1.lower().strip(),
        title2.lower().strip()
    ).ratio() * 100


# --------------------------------------------------
# SMART PRIORITY
# --------------------------------------------------

def calculate_smart_priority(
    severity: str,
    urgency: str
) -> dict:

    severity_weight = {
        "CRITICAL": 4,
        "MAJOR": 3,
        "MINOR": 2,
        "TRIVIAL": 1
    }

    urgency_weight = {
        "CRITICAL": 3,
        "HIGH": 3,
        "MEDIUM": 2,
        "LOW": 1
    }

    score = (
        severity_weight.get(severity.upper(), 1)
        * urgency_weight.get(urgency.upper(), 1)
    )

    if score >= 10:
        level = "URGENT"
    elif score >= 7:
        level = "HIGH"
    elif score >= 4:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {
        "score": score,
        "level": level
    }


# --------------------------------------------------
# DEVELOPER MATCHING
# --------------------------------------------------

def calculate_developer_matching(
    issue_title: str,
    issue_description: str,
    developers: list,
    db: Session
):

    issue_text = (
        f"{issue_title} {issue_description}"
    ).lower()

    results = []

    for developer in developers:

        skills = (
            developer.core_skills or ""
        ).lower()

        matched_skills = []

        for skill in skills.split(","):

            skill = skill.strip()

            if skill and skill in issue_text:
                matched_skills.append(skill)

        # Count active tasks of developer
        active_tasks = (
            db.query(Issue)
            .filter(
                Issue.assignee_id == developer.id,
                Issue.status.notin_(
                    ["CLOSED", "RESOLVED"]
                )
            )
            .count()
        )

        # Matching score
        score = (
            50
            + (25 * len(matched_skills))
            - (5 * active_tasks)
        )

        # Keep score between 0 and 100
        score = max(0, min(score, 100))

        results.append({
            "developer_id": developer.id,
            "developer_name": (
                developer.full_name
                or developer.username
            ),
            "team": developer.team,
            "core_skills": developer.core_skills,
            "proficiency": developer.proficiency,
            "matched_skills": matched_skills,
            "active_tasks": active_tasks,
            "matching_score": score
        })

    # Highest score first
    results.sort(
        key=lambda x: x["matching_score"],
        reverse=True
    )

    # Top 3 developers
    return results[:3]


# --------------------------------------------------
# CREATE ISSUE REQUEST
# --------------------------------------------------

class CreateIssueRequest(BaseModel):

    title: str
    description: str

    severity: Severity
    priority: Priority

    project_id: int
    category_id: int

    reproduction_steps: str = ""
    affected_modules: str = ""
    environment_details: str = ""

    estimated_effort: float | None = None
    assignee_id: int | None = None

    issue_type: str = "BUG"

# --------------------------------------------------
# UPDATE ISSUE REQUEST
# --------------------------------------------------

class UpdateIssueRequest(BaseModel):
    title: str | None = None
    description: str | None = None

    severity: Severity | None = None
    priority: Priority | None = None

    category_id: int | None = None

    reproduction_steps: str | None = None
    affected_modules: str | None = None
    environment_details: str | None = None

    estimated_effort: float | None = None
    issue_type: str | None = None

# --------------------------------------------------
# CREATE ISSUE
# --------------------------------------------------

@router.post("/")
def create_issue(
    request: CreateIssueRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    project = db.get(
        Project,
        request.project_id
    )

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found"
        )

    category = db.get(
        BugCategory,
        request.category_id
    )

    if not category:
        raise HTTPException(
            status_code=404,
            detail="Bug category not found"
        )

    # Validate assignee
    if request.assignee_id is not None:

        assignee = db.get(
            User,
            request.assignee_id
        )

        if not assignee:
            raise HTTPException(
                status_code=404,
                detail="Assignee not found"
            )

        if assignee.role != UserRole.DEVELOPER.value:
            raise HTTPException(
                status_code=400,
                detail="Assignee must be a DEVELOPER"
            )

    # Generate unique issue key
    existing_keys = (
        db.query(Issue.issue_key).all()
    )

    numbers = []

    for (key,) in existing_keys:

        if key and key.startswith("B-"):

            try:
                numbers.append(
                    int(key.split("-")[1])
                )
            except ValueError:
                pass

    next_number = (
        max(numbers, default=0) + 1
    )

    issue_key = f"B-{next_number:03d}"

    # Smart Priority
    smart_priority = calculate_smart_priority(
        request.severity.value,
        request.priority.value
    )

    # Create issue
    issue = Issue(
        issue_key=issue_key,
        issue_type=request.issue_type,
        title=request.title,
        description=request.description,
        reproduction_steps=request.reproduction_steps,
        severity=request.severity.value,
        priority=request.priority.value,
        status=IssueStatus.REPORTED.value,
        project_id=request.project_id,
        project_key=project.project_key,
        category_id=request.category_id,
        reporter_id=current_user.id,
        assignee_id=request.assignee_id,
        affected_modules=request.affected_modules,
        environment_details=request.environment_details,
        estimated_effort=request.estimated_effort or 0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    db.add(issue)
    db.commit()
    db.refresh(issue)

    # Audit log
    audit = AuditLog(
        issue_id=issue.id,
        user_id=current_user.id,
        action="ISSUE_CREATED",
        field_name=None,
        old_value=None,
        new_value=issue.title,
        timestamp=datetime.now(timezone.utc)
    )

    db.add(audit)
    db.commit()

    return {
        "message": "Issue created successfully",
        "issue_id": issue.id,
        "issue_key": issue.issue_key,
        "title": issue.title,
        "status": issue.status,
        "smart_priority_score": smart_priority["score"],
        "smart_priority_level": smart_priority["level"]
    }
# --------------------------------------------------
# UPDATE ISSUE
# --------------------------------------------------

@router.patch("/{issue_id}")
def update_issue(
    issue_id: int,
    request: UpdateIssueRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    issue = db.get(Issue, issue_id)

    if not issue:
        raise HTTPException(
            status_code=404,
            detail="Issue not found"
        )

    # Validate category if provided
    if request.category_id is not None:

        category = db.get(
            BugCategory,
            request.category_id
        )

        if not category:
            raise HTTPException(
                status_code=404,
                detail="Bug category not found"
            )

    changes = []
@router.delete("/{issue_id}")
def delete_issue(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN)
    )
):
    issue = db.get(Issue, issue_id)

    if not issue:
        raise HTTPException(
            status_code=404,
            detail="Issue not found"
        )

    issue_key = issue.issue_key

    # Delete audit logs related to this issue first
    db.query(AuditLog).filter(
        AuditLog.issue_id == issue_id
    ).delete(
        synchronize_session=False
    )

    # Delete the issue
    db.delete(issue)

    db.commit()

    return {
        "message": "Issue deleted successfully",
        "issue_id": issue_id,
        "issue_key": issue_key
    }

    # -----------------------------
    # TITLE
    # -----------------------------
    if request.title is not None:
        if request.title != issue.title:

            changes.append({
                "field": "title",
                "old": issue.title,
                "new": request.title
            })

            issue.title = request.title

    # -----------------------------
    # DESCRIPTION
    # -----------------------------
    if request.description is not None:
        if request.description != issue.description:

            changes.append({
                "field": "description",
                "old": issue.description,
                "new": request.description
            })

            issue.description = request.description

    # -----------------------------
    # SEVERITY
    # -----------------------------
    if request.severity is not None:

        new_value = request.severity.value

        if new_value != issue.severity:

            changes.append({
                "field": "severity",
                "old": issue.severity,
                "new": new_value
            })

            issue.severity = new_value

    # -----------------------------
    # PRIORITY
    # -----------------------------
    if request.priority is not None:

        new_value = request.priority.value

        if new_value != issue.priority:

            changes.append({
                "field": "priority",
                "old": issue.priority,
                "new": new_value
            })

            issue.priority = new_value

    # -----------------------------
    # CATEGORY
    # -----------------------------
    if request.category_id is not None:

        if request.category_id != issue.category_id:

            changes.append({
                "field": "category_id",
                "old": str(issue.category_id),
                "new": str(request.category_id)
            })

            issue.category_id = request.category_id

    # -----------------------------
    # REPRODUCTION STEPS
    # -----------------------------
    if request.reproduction_steps is not None:

        if request.reproduction_steps != issue.reproduction_steps:

            changes.append({
                "field": "reproduction_steps",
                "old": issue.reproduction_steps,
                "new": request.reproduction_steps
            })

            issue.reproduction_steps = request.reproduction_steps

    # -----------------------------
    # AFFECTED MODULES
    # -----------------------------
    if request.affected_modules is not None:

        if request.affected_modules != issue.affected_modules:

            changes.append({
                "field": "affected_modules",
                "old": issue.affected_modules,
                "new": request.affected_modules
            })

            issue.affected_modules = request.affected_modules

    # -----------------------------
    # ENVIRONMENT
    # -----------------------------
    if request.environment_details is not None:

        if request.environment_details != issue.environment_details:

            changes.append({
                "field": "environment_details",
                "old": issue.environment_details,
                "new": request.environment_details
            })

            issue.environment_details = request.environment_details

    # -----------------------------
    # ESTIMATED EFFORT
    # -----------------------------
    if request.estimated_effort is not None:

        if request.estimated_effort != issue.estimated_effort:

            changes.append({
                "field": "estimated_effort",
                "old": str(issue.estimated_effort),
                "new": str(request.estimated_effort)
            })

            issue.estimated_effort = request.estimated_effort

    # -----------------------------
    # ISSUE TYPE
    # -----------------------------
    if request.issue_type is not None:

        if request.issue_type != issue.issue_type:

            changes.append({
                "field": "issue_type",
                "old": issue.issue_type,
                "new": request.issue_type
            })

            issue.issue_type = request.issue_type

    # -----------------------------
    # CHECK CHANGES
    # -----------------------------
    if not changes:

        raise HTTPException(
            status_code=400,
            detail="No changes provided"
        )

    issue.updated_at = datetime.now(timezone.utc)

    # -----------------------------
    # AUDIT LOG
    # -----------------------------
    for change in changes:

        audit = AuditLog(
            issue_id=issue.id,
            user_id=current_user.id,
            action="ISSUE_UPDATED",
            field_name=change["field"],
            old_value=change["old"],
            new_value=change["new"],
            timestamp=datetime.now(timezone.utc)
        )

        db.add(audit)

    db.commit()
    db.refresh(issue)

    return {
        "message": "Issue updated successfully",
        "issue_id": issue.id,
        "issue_key": issue.issue_key,
        "updated_fields": [
            change["field"]
            for change in changes
        ],
        "updated_issue": {
            "title": issue.title,
            "description": issue.description,
            "severity": issue.severity,
            "priority": issue.priority,
            "category_id": issue.category_id,
            "reproduction_steps": issue.reproduction_steps,
            "affected_modules": issue.affected_modules,
            "environment_details": issue.environment_details,
            "estimated_effort": issue.estimated_effort,
            "issue_type": issue.issue_type
        }
    }

# --------------------------------------------------
# GET ALL ISSUES WITH FILTERS
# --------------------------------------------------

@router.get("/")
def get_issues(
    project_id: int | None = None,
    status: str | None = None,
    severity: str | None = None,
    assignee_id: int | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    query = db.query(Issue)

    if project_id is not None:
        query = query.filter(
            Issue.project_id == project_id
        )

    if status is not None:
        query = query.filter(
            Issue.status == status
        )

    if severity is not None:
        query = query.filter(
            Issue.severity == severity
        )

    if assignee_id is not None:
        query = query.filter(
            Issue.assignee_id == assignee_id
        )

    if search is not None and search.strip():

        search_text = (
            f"%{search.strip()}%"
        )

        query = query.filter(
            (Issue.issue_key.ilike(search_text))
            |
            (Issue.title.ilike(search_text))
        )

    issues = (
        query
        .order_by(Issue.created_at.desc())
        .all()
    )

    return [
        {
            "id": issue.id,
            "issue_key": issue.issue_key,
            "title": issue.title,
            "severity": issue.severity,
            "priority": issue.priority,
            "status": issue.status,
            "project_id": issue.project_id,
            "reporter_id": issue.reporter_id,
            "assignee_id": issue.assignee_id,
            "sprint_id": issue.sprint_id,
        }
        for issue in issues
    ]


# --------------------------------------------------
# GET SINGLE ISSUE WITH AUDIT HISTORY
# --------------------------------------------------

@router.get("/{issue_id}")
def get_issue(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    issue = db.get(
        Issue,
        issue_id
    )

    if not issue:
        raise HTTPException(
            status_code=404,
            detail="Issue not found"
        )

    audit_logs = (
        db.query(AuditLog)
        .filter(
            AuditLog.issue_id == issue_id
        )
        .order_by(
            AuditLog.timestamp.asc()
        )
        .all()
    )

    return {
        "id": issue.id,
        "issue_key": issue.issue_key,
        "title": issue.title,
        "description": issue.description,
        "reproduction_steps": issue.reproduction_steps,
        "severity": issue.severity,
        "priority": issue.priority,
        "status": issue.status,
        "project_id": issue.project_id,
        "category_id": issue.category_id,
        "reporter_id": issue.reporter_id,
        "assignee_id": issue.assignee_id,
        "affected_modules": issue.affected_modules,
        "environment_details": issue.environment_details,
        "estimated_effort": issue.estimated_effort,
        "created_at": issue.created_at,
        "updated_at": issue.updated_at,
        "resolved_at": issue.resolved_at,

        "audit_history": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "action": log.action,
                "field_name": log.field_name,
                "old_value": log.old_value,
                "new_value": log.new_value,
                "timestamp": log.timestamp
            }
            for log in audit_logs
        ]
    }


# --------------------------------------------------
# UPDATE STATUS
# --------------------------------------------------

@router.patch("/{issue_id}/status")
def update_status(
    issue_id: int,
    status: IssueStatus,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.DEVELOPER,
            UserRole.TESTER,
            UserRole.ADMIN
        )
    )
):

    issue = db.get(
        Issue,
        issue_id
    )

    if not issue:
        raise HTTPException(
            status_code=404,
            detail="Issue not found"
        )

    allowed_transitions = {

        "REPORTED": [
            "TRIAGED"
        ],

        "TRIAGED": [
            "IN_PROGRESS"
        ],

        "IN_PROGRESS": [
            "CODE_REVIEW"
        ],

        "CODE_REVIEW": [
            "QA_VERIFICATION"
        ],

        "QA_VERIFICATION": [
            "RESOLVED"
        ],

        "RESOLVED": [
            "CLOSED",
            "IN_PROGRESS"
        ],

        "CLOSED": [
            "IN_PROGRESS"
        ]
    }

    current_status = issue.status
    requested_status = status.value

    if requested_status not in allowed_transitions.get(
        current_status,
        []
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid transition: "
                f"{current_status} -> "
                f"{requested_status}"
            )
        )

    old_status = issue.status

    issue.status = requested_status

    issue.updated_at = (
        datetime.now(timezone.utc)
    )

    if requested_status in [
        "RESOLVED",
        "CLOSED"
    ]:

        issue.resolved_at = (
            datetime.now(timezone.utc)
        )

    audit = AuditLog(
        issue_id=issue.id,
        user_id=current_user.id,
        action="STATUS_CHANGED",
        field_name="status",
        old_value=old_status,
        new_value=requested_status,
        timestamp=datetime.now(timezone.utc)
    )

    db.add(audit)

    db.commit()
    db.refresh(issue)

    return {
        "message":
            "Issue status updated successfully",

        "issue_key":
            issue.issue_key,

        "old_status":
            old_status,

        "new_status":
            issue.status
    }


# --------------------------------------------------
# ASSIGN ISSUE
# --------------------------------------------------

@router.patch("/{issue_id}/assign")
def assign_issue(
    issue_id: int,
    assignee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.TRIAGER,
            UserRole.ADMIN,
            UserRole.DEVELOPER
        )
    )
):

    issue = db.get(
        Issue,
        issue_id
    )

    if not issue:
        raise HTTPException(
            status_code=404,
            detail="Issue not found"
        )

    assignee = db.get(
        User,
        assignee_id
    )

    if not assignee:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    if assignee.role != UserRole.DEVELOPER.value:

        raise HTTPException(
            status_code=400,
            detail=(
                "Issue can only be assigned "
                "to a DEVELOPER"
            )
        )

    old_assignee = issue.assignee_id

    issue.assignee_id = assignee_id

    issue.updated_at = (
        datetime.now(timezone.utc)
    )

    audit = AuditLog(
        issue_id=issue.id,
        user_id=current_user.id,
        action="ISSUE_ASSIGNED",
        field_name="assignee_id",
        old_value=(
            str(old_assignee)
            if old_assignee
            else None
        ),
        new_value=str(assignee_id),
        timestamp=datetime.now(timezone.utc)
    )

    db.add(audit)

    db.commit()

    return {
        "message":
            "Issue assigned successfully",

        "issue_key":
            issue.issue_key,

        "assignee_id":
            assignee_id
    }


# --------------------------------------------------
# UPDATE PRIORITY
# --------------------------------------------------

@router.patch("/{issue_id}/priority")
def update_priority(
    issue_id: int,
    priority: Priority,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    issue = db.get(
        Issue,
        issue_id
    )

    if not issue:
        raise HTTPException(
            status_code=404,
            detail="Issue not found"
        )

    old_priority = issue.priority
    new_priority = priority.value

    if old_priority == new_priority:

        raise HTTPException(
            status_code=400,
            detail=(
                "New priority is same "
                "as current priority"
            )
        )

    issue.priority = new_priority

    issue.updated_at = (
        datetime.now(timezone.utc)
    )

    audit = AuditLog(
        issue_id=issue.id,
        user_id=current_user.id,
        action="PRIORITY_CHANGED",
        field_name="priority",
        old_value=old_priority,
        new_value=new_priority,
        timestamp=datetime.now(timezone.utc)
    )

    db.add(audit)

    db.commit()
    db.refresh(issue)

    return {
        "message":
            "Issue priority updated successfully",

        "issue_key":
            issue.issue_key,

        "old_priority":
            old_priority,

        "new_priority":
            issue.priority
    }


# --------------------------------------------------
# CHECK DUPLICATES
# --------------------------------------------------

@router.post("/check-duplicates")
def check_duplicates(
    title: str,
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    issues = (
        db.query(Issue)
        .filter(
            Issue.project_id == project_id,
            Issue.status.notin_(
                ["CLOSED", "RESOLVED"]
            )
        )
        .all()
    )

    duplicates = []

    for issue in issues:

        similarity = calculate_similarity(
            title,
            issue.title
        )

        if similarity >= 55:

            duplicates.append({
                "issue_id": issue.id,
                "issue_key": issue.issue_key,
                "title": issue.title,
                "similarity": round(
                    similarity,
                    2
                ),
                "warning":
                    "Possible duplicate issue"
            })

    return {
        "is_duplicate":
            len(duplicates) > 0,

        "duplicates":
            duplicates
    }


# --------------------------------------------------
# DEVELOPER MATCHING
# --------------------------------------------------

@router.get("/{issue_id}/developer-matches")
def get_developer_matches(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    issue = db.get(
        Issue,
        issue_id
    )

    if not issue:
        raise HTTPException(
            status_code=404,
            detail="Issue not found"
        )

    developers = (
        db.query(User)
        .filter(
            User.role == UserRole.DEVELOPER.value,
            User.is_active == True
        )
        .all()
    )

    matches = calculate_developer_matching(
        issue.title,
        issue.description,
        developers,
        db
    )

    return {
        "issue_id": issue.id,
        "issue_key": issue.issue_key,
        "matches": matches
    }

# --------------------------------------------------
# MERGE ISSUES
# --------------------------------------------------

@router.patch("/{issue_id}/merge/{target_issue_id}")
def merge_issues(
    issue_id: int,
    target_issue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.TRIAGER,
            UserRole.ADMIN
        )
    )
):

    if issue_id == target_issue_id:
        raise HTTPException(
            status_code=400,
            detail="An issue cannot be merged with itself"
        )

    source_issue = db.get(
        Issue,
        issue_id
    )

    if not source_issue:
        raise HTTPException(
            status_code=404,
            detail="Source issue not found"
        )

    target_issue = db.get(
        Issue,
        target_issue_id
    )

    if not target_issue:
        raise HTTPException(
            status_code=404,
            detail="Target issue not found"
        )

    # Only open issues can be merged
    if source_issue.status in ["CLOSED", "RESOLVED"]:
        raise HTTPException(
            status_code=400,
            detail="Closed or resolved issue cannot be merged"
        )

    if target_issue.status in ["CLOSED", "RESOLVED"]:
        raise HTTPException(
            status_code=400,
            detail="Target issue is already closed or resolved"
        )

    old_status = source_issue.status

    # Mark source issue as closed after merge
    source_issue.status = "CLOSED"
    source_issue.updated_at = datetime.now(timezone.utc)

    # Store merge information in audit log
    audit = AuditLog(
        issue_id=source_issue.id,
        user_id=current_user.id,
        action="ISSUE_MERGED",
        field_name="merged_into",
        old_value=old_status,
        new_value=target_issue.issue_key,
        timestamp=datetime.now(timezone.utc)
    )

    db.add(audit)

    db.commit()
    db.refresh(source_issue)

    return {
        "message": "Issue merged successfully",
        "source_issue": {
            "id": source_issue.id,
            "issue_key": source_issue.issue_key,
            "status": source_issue.status
        },
        "target_issue": {
            "id": target_issue.id,
            "issue_key": target_issue.issue_key,
            "status": target_issue.status
        }
    }

# --------------------------------------------------
# TRIAGE RECOMMENDATION
# --------------------------------------------------

@router.post("/triage-recommendation")
def triage_recommendation(
    severity: Severity,
    urgency: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Calculate smart priority
    priority_result = calculate_smart_priority(
        severity.value,
        urgency
    )

    return {
        "severity": severity.value,
        "urgency": urgency.upper(),
        "smart_priority_score": priority_result["score"],
        "smart_priority_level": priority_result["level"]
    }
@router.post("/{issue_id}/tags")
def add_tag_to_issue(
    issue_id: int,
    name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    issue = db.get(Issue, issue_id)

    if not issue:
        raise HTTPException(
            status_code=404,
            detail="Issue not found"
        )

    # Clean tag name
    tag_name = name.strip().lower()

    if not tag_name:
        raise HTTPException(
            status_code=400,
            detail="Tag name cannot be empty"
        )

    # Check if tag already exists
    tag = db.query(Tag).filter(
        Tag.name == tag_name
    ).first()

    # Create new tag if needed
    if not tag:
        tag = Tag(name=tag_name)
        db.add(tag)
        db.flush()

    # Check whether tag is already attached
    existing = db.execute(
        issue_tags.select().where(
            issue_tags.c.issue_id == issue_id,
            issue_tags.c.tag_id == tag.id
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Tag already added to this issue"
        )

    # Connect issue and tag
    db.execute(
        issue_tags.insert().values(
            issue_id=issue_id,
            tag_id=tag.id
        )
    )

    db.commit()

    return {
        "message": "Tag added successfully",
        "issue_id": issue_id,
        "tag": tag.name
    }
@router.get("/{issue_id}/tags")
def get_issue_tags(
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

    rows = db.execute(
        issue_tags.select().where(
            issue_tags.c.issue_id == issue_id
        )
    ).fetchall()

    tag_ids = [row.tag_id for row in rows]

    if not tag_ids:
        return {
            "issue_id": issue_id,
            "tags": []
        }

    tags = db.query(Tag).filter(
        Tag.id.in_(tag_ids)
    ).all()

    return {
        "issue_id": issue_id,
        "tags": [tag.name for tag in tags]
    }
@router.delete("/{issue_id}/tags/{tag_id}")
def remove_tag_from_issue(
    issue_id: int,
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    issue = db.get(Issue, issue_id)

    if not issue:
        raise HTTPException(
            status_code=404,
            detail="Issue not found"
        )

    tag = db.get(Tag, tag_id)

    if not tag:
        raise HTTPException(
            status_code=404,
            detail="Tag not found"
        )

    existing = db.execute(
        issue_tags.select().where(
            issue_tags.c.issue_id == issue_id,
            issue_tags.c.tag_id == tag_id
        )
    ).first()

    if not existing:
        raise HTTPException(
            status_code=404,
            detail="Tag is not attached to this issue"
        )

    db.execute(
        issue_tags.delete().where(
            issue_tags.c.issue_id == issue_id,
            issue_tags.c.tag_id == tag_id
        )
    )

    db.commit()

    return {
        "message": "Tag removed successfully",
        "issue_id": issue_id,
        "tag": tag.name
    }