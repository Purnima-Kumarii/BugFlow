from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Project, User
from ..auth import get_current_user, require_roles, UserRole

router = APIRouter(
    prefix="/api/v1/projects",
    tags=["Projects"]
)


@router.post("/")
def create_project(
    project_key: str,
    name: str,
    description: str = "",
    codebase: str = "",
    development_cycle: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.TRIAGER)
    )
):
    existing = db.query(Project).filter(
        Project.project_key == project_key
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Project key already exists"
        )

    project = Project(
        project_key=project_key,
        name=name,
        description=description,
        codebase=codebase,
        development_cycle=development_cycle
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    return {
        "message": "Project created successfully",
        "project_id": project.id,
        "project_key": project.project_key,
        "name": project.name
    }


@router.get("/")
def get_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    projects = db.query(Project).all()

    return [
        {
            "id": project.id,
            "project_key": project.project_key,
            "name": project.name,
            "description": project.description,
            "codebase": project.codebase,
            "development_cycle": project.development_cycle
        }
        for project in projects
    ]