from io import BytesIO
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from ..auth import current_user
from ..database import get_db
from ..detection import evaluate_event
from ..models import SecurityEvent, Alert, User
from ..schemas import EventIn, EventOut
from ..websocket import manager


router = APIRouter(prefix="/api/events", tags=["Events"])


@router.get("", response_model=list[EventOut])
def list_events(
    limit: int = Query(100, ge=1, le=500),
    severity: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    query = db.query(SecurityEvent)

    if severity:
        query = query.filter(SecurityEvent.severity == severity)

    return (
        query.order_by(SecurityEvent.timestamp.desc())
        .limit(limit)
        .all()
    )


@router.post("/ingest", response_model=EventOut)
async def ingest(
    payload: EventIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    event = SecurityEvent(**payload.model_dump(exclude_none=True))

    db.add(event)
    db.commit()
    db.refresh(event)

    alerts = evaluate_event(db, event)

    await manager.broadcast({
        "type": "event",
        "event": {
            "id": event.id,
            "source": event.source,
            "event_type": event.event_type,
            "severity": event.severity,
            "source_ip": event.source_ip,
            "message": event.message,
        },
        "alerts_created": len(alerts),
    })

    for alert in alerts:
        await manager.broadcast({
            "type": "alert",
            "alert": {
                "id": alert.id,
                "title": alert.title,
                "severity": alert.severity,
                "status": alert.status,
            },
        })

    return event


@router.get("/{event_id}/report")
def generate_event_report(
    event_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    event = (
        db.query(SecurityEvent)
        .filter(SecurityEvent.id == event_id)
        .first()
    )

    if event is None:
        raise HTTPException(
            status_code=404,
            detail="Event not found",
        )

    alerts = (
        db.query(Alert)
        .filter(Alert.event_id == event_id)
        .order_by(Alert.created_at.desc())
        .all()
    )

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=20,
        spaceAfter=12,
    )

    heading_style = ParagraphStyle(
        "ReportHeading",
        parent=styles["Heading2"],
        fontSize=13,
        spaceBefore=10,
        spaceAfter=6,
    )

    normal_style = ParagraphStyle(
        "ReportBody",
        parent=styles["BodyText"],
        fontSize=9,
        leading=13,
        wordWrap="CJK",
    )

    def safe_text(value):
        if value is None or str(value).strip() == "":
            return "N/A"
        return escape(str(value)).replace("\n", "<br/>")

    story = [
        Paragraph("SOC SENTINEL", title_style),
        Paragraph("Single Security Event Report", styles["Heading2"]),
        Spacer(1, 8),
        Paragraph("Event Information", heading_style),
    ]

    event_data = [
        ["Event ID", str(event.id)],
        ["Event Type", safe_text(event.event_type)],
        ["Source", safe_text(event.source)],
        ["Severity", safe_text(event.severity)],
        ["Source IP", safe_text(event.source_ip)],
        ["Destination IP", safe_text(event.destination_ip)],
        ["Username", safe_text(event.username)],
        ["Hostname", safe_text(event.hostname)],
        ["Timestamp", safe_text(event.timestamp)],
    ]

    event_table = Table(
        event_data,
        colWidths=[42 * mm, 125 * mm],
        repeatRows=0,
    )

    event_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))

    story.append(event_table)

    story.append(Paragraph("Event Message", heading_style))
    story.append(Paragraph(safe_text(event.message), normal_style))

    if event.raw_log:
        story.append(Paragraph("Raw Log", heading_style))
        story.append(Paragraph(safe_text(event.raw_log), normal_style))

    story.append(
        Paragraph("Related Detection Alerts", heading_style)
    )

    if alerts:
        alert_data = [
            ["Alert ID", "Rule ID", "Title", "Severity", "Status"]
        ]

        for alert in alerts:
            alert_data.append([
                str(alert.id),
                safe_text(alert.rule_id),
                safe_text(alert.title),
                safe_text(alert.severity),
                safe_text(alert.status),
            ])

        alert_table = Table(
            alert_data,
            colWidths=[
                18 * mm,
                28 * mm,
                62 * mm,
                27 * mm,
                27 * mm,
            ],
            repeatRows=1,
        )

        alert_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))

        story.append(alert_table)

    else:
        story.append(
            Paragraph(
                "No detection alert was generated for this event.",
                normal_style,
            )
        )

    story.append(Spacer(1, 15))
    story.append(
        Paragraph("Generated by SOC Sentinel", normal_style)
    )

    doc.build(story)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="SOC_Event_{event.id}_Report.pdf"'
            )
        },
    )

