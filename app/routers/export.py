from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.database import get_db
from app.models import Issue
from app.auth import get_current_user


router = APIRouter(
    prefix="/api/v1/export",
    tags=["Export"]
)


@router.get("/pdf")
def export_pdf(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    issues = db.query(Issue).all()

    from io import BytesIO

    buffer = BytesIO()

    pdf = canvas.Canvas(
        buffer,
        pagesize=A4
    )

    width, height = A4

    y = height - 50

    pdf.setFont(
        "Helvetica-Bold",
        18
    )

    pdf.drawString(
        50,
        y,
        "BUGFLOW - ISSUE REPORT"
    )

    y -= 35

    pdf.setFont(
        "Helvetica",
        10
    )

    for issue in issues:

        if y < 70:
            pdf.showPage()
            y = height - 50

        pdf.setFont(
            "Helvetica-Bold",
            11
        )

        pdf.drawString(
            50,
            y,
            f"Issue: {issue.issue_key}"
        )

        y -= 18

        pdf.setFont(
            "Helvetica",
            10
        )

        pdf.drawString(
            50,
            y,
            f"Title: {issue.title[:90]}"
        )

        y -= 15

        pdf.drawString(
            50,
            y,
            f"Status: {issue.status}"
        )

        y -= 15

        pdf.drawString(
            50,
            y,
            f"Severity: {issue.severity}"
        )

        y -= 25

        pdf.line(
            50,
            y,
            width - 50,
            y
        )

        y -= 20

    pdf.save()

    pdf_data = buffer.getvalue()

    buffer.close()

    return Response(
        content=pdf_data,
        media_type="application/pdf",
        headers={
            "Content-Disposition":
                "attachment; filename=bugflow-report.pdf"
        }
    )


@router.get("/csv")
def export_csv(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    issues = db.query(Issue).all()

    csv_content = "Issue Key,Title,Status,Severity\n"

    for issue in issues:

        csv_content += (
            f'"{issue.issue_key}",'
            f'"{issue.title}",'
            f'"{issue.status}",'
            f'"{issue.severity}"\n'
        )

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition":
                "attachment; filename=bugflow-report.csv"
        }
    )