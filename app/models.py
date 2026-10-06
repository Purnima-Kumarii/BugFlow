from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import DateTime, Enum as SAEnum, Integer, String, Text, Float, Boolean, Column, Table, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


# =========================
# ENUMS
# =========================

class UserRole(str, Enum):
    ADMIN = "ADMIN"
    DEVELOPER = "DEVELOPER"
    TESTER = "TESTER"
    TRIAGER = "TRIAGER"
    STAKEHOLDER = "STAKEHOLDER"


class IssueType(str, Enum):
    BUG = "BUG"
    FEATURE_REQUEST = "FEATURE_REQUEST"
    ENHANCEMENT = "ENHANCEMENT"
    TECHNICAL_DEBT = "TECHNICAL_DEBT"
    SUPPORT_TICKET = "SUPPORT_TICKET"


class Severity(str, Enum):
    MINOR = "MINOR"
    MAJOR = "MAJOR"
    CRITICAL = "CRITICAL"
    TRIVIAL = "TRIVIAL"


class Priority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class IssueStatus(str, Enum):
    REPORTED = "REPORTED"
    TRIAGED = "TRIAGED"
    IN_PROGRESS = "IN_PROGRESS"
    CODE_REVIEW = "CODE_REVIEW"
    QA_VERIFICATION = "QA_VERIFICATION"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


# =========================
# USERS
# =========================

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)

    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, native_enum=False),
        nullable=False
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    full_name: Mapped[str | None] = mapped_column(String(255))
    team: Mapped[str | None] = mapped_column(String(255))
    core_skills: Mapped[str | None] = mapped_column(String(500))
    proficiency: Mapped[str | None] = mapped_column(String(100))

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )


# =========================
# PROJECTS
# =========================

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    project_key: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )

    description: Mapped[str | None] = mapped_column(Text)
    codebase: Mapped[str | None] = mapped_column(String(200))
    development_cycle: Mapped[str | None] = mapped_column(String(100))

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )


# =========================
# BUG CATEGORIES
# =========================

class BugCategory(Base):
    __tablename__ = "bug_categories"

    category_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    category_name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False
    )

    urgency: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )


# =========================
# ISSUES
# =========================

class Issue(Base):
    __tablename__ = "issues"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    issue_key: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        index=True
    )

    issue_type: Mapped[IssueType] = mapped_column(
        SAEnum(IssueType, native_enum=False),
        nullable=False
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    reproduction_steps: Mapped[str | None] = mapped_column(Text)

    severity: Mapped[Severity] = mapped_column(
        SAEnum(Severity, native_enum=False),
        nullable=False
    )

    priority: Mapped[Priority] = mapped_column(
        SAEnum(Priority, native_enum=False),
        nullable=False
    )

    status: Mapped[IssueStatus] = mapped_column(
        SAEnum(IssueStatus, native_enum=False),
        nullable=False,
        default=IssueStatus.REPORTED
    )

    affected_module: Mapped[str | None] = mapped_column(String(150))
    environment: Mapped[str | None] = mapped_column(String(150))
    screenshot_url: Mapped[str | None] = mapped_column(String(500))

    project_key: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True
    )

    reporter_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    assignee_id: Mapped[int | None] = mapped_column(Integer)

    project_id: Mapped[int | None] = mapped_column(Integer)
    category_id: Mapped[int | None] = mapped_column(Integer)
    sprint_id: Mapped[int | None] = mapped_column(Integer)

    dev_stage: Mapped[str | None] = mapped_column(String(30))

    affected_modules: Mapped[str | None] = mapped_column(
        String(200)
    )

    environment_details: Mapped[str | None] = mapped_column(
        String(300)
    )

    estimated_effort: Mapped[float | None] = mapped_column(Float)

    priority_score: Mapped[float | None] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime
    )
# =========================
# ISSUE TAG ASSOCIATION
# =========================

issue_tags = Table(
    "issue_tags",
    Base.metadata,
    Column(
        "issue_id",
        Integer,
        ForeignKey("issues.id", ondelete="CASCADE"),
        primary_key=True
    ),
    Column(
        "tag_id",
        Integer,
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True
    ),
)

class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )

# =========================
# AUDIT LOG
# =========================

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    issue_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    field_name: Mapped[str | None] = mapped_column(
        String(100)
    )

    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )


# =========================
# ACTIVITY LOG
# =========================

class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    issue_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    details: Mapped[str | None] = mapped_column(Text)

    user_id: Mapped[int | None] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
class Sprint(Base):
    __tablename__ = "sprints"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    project_id = Column(Integer, nullable=False)
    goal = Column(Text, nullable=True)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    status = Column(String(30), default="PLANNED")
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc)
    )