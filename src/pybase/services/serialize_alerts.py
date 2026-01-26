"""
Alert management for serialization pipeline.

Alerts on:
- Low element_coverage (< 80% warning, < 50% critical)
- High failure rate (> 10% warning, > 25% critical)
- Database issues (bloat, cache misses, connection issues)
- Processing stalls (no progress in N minutes)
Email notifications for critical issues.
"""

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from smtplib import SMTP
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.logging import get_logger

logger = get_logger(__name__)


# Alert types and severities
class AlertSeverity:
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType:
    LOW_COVERAGE = "low_element_coverage"
    HIGH_FAILURE_RATE = "high_failure_rate"
    PROCESSING_STALL = "processing_stall"
    DB_BLOAT = "database_bloat"
    DB_CACHE_MISS = "low_cache_hit_ratio"
    CONNECTION_ERROR = "connection_error"
    DISK_SPACE = "low_disk_space"


@dataclass
class Alert:
    """Serialization alert."""
    alert_id: str
    alert_type: str
    severity: str
    title: str
    message: str
    timestamp: datetime
    model_name: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolved_at: datetime | None = None
    notification_sent: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "alert_id": self.alert_id,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "title": self.title,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "model_name": self.model_name,
            "metrics": self.metrics,
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "notification_sent": self.notification_sent,
        }


class SerializeAlertManager:
    """
    Manage alerts for serialization pipeline.

    Checks:
    - Quality metrics (element_coverage, unrecoverable_unknown)
    - Failure rates
    - Processing activity
    - Database health
    """

    # Thresholds
    COVERAGE_WARNING = 80.0
    COVERAGE_CRITICAL = 50.0

    FAILURE_RATE_WARNING = 0.10  # 10%
    FAILURE_RATE_CRITICAL = 0.25  # 25%

    STALL_MINUTES = 15  # No processing for 15 minutes = stall

    # Min time between same alerts (minutes)
    ALERT_COOLDOWN_MINUTES = 30

    def __init__(
        self,
        smtp_host: str | None = None,
        smtp_port: int = 587,
        smtp_user: str | None = None,
        smtp_password: str | None = None,
        from_email: str | None = None,
        to_emails: list[str] | None = None,
    ):
        self.smtp_host = smtp_host or os.getenv("SMTP_HOST")
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user or os.getenv("SMTP_USER")
        self.smtp_password = smtp_password or os.getenv("SMTP_PASSWORD")
        self.from_email = from_email or os.getenv("ALERT_FROM_EMAIL", "alerts@pybase.local")
        self.to_emails = to_emails or self._parse_email_list(os.getenv("ALERT_TO_EMAILS", ""))

        self._alerts: dict[str, Alert] = {}
        self._alert_history: dict[str, datetime] = {}  # Track last alert time per type

    def _parse_email_list(self, emails_str: str) -> list[str]:
        """Parse comma-separated email list."""
        if not emails_str:
            return []
        return [e.strip() for e in emails_str.split(",") if e.strip()]

    def _generate_alert_id(self, alert_type: str, model_name: str | None = None) -> str:
        """Generate unique alert ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        model_suffix = f"_{model_name}" if model_name else ""
        return f"{alert_type}{model_suffix}_{timestamp}"

    async def check_quality_alerts(
        self,
        session: AsyncSession,
    ) -> list[Alert]:
        """Check for quality metric alerts."""
        alerts = []

        sql = text("""
            SELECT
                model_name,
                (serialized_content->>'element_coverage')::float as coverage,
                (serialized_content->>'unrecoverable_unknown')::int as unknown,
                created_at
            FROM serialized_models
            WHERE serialized_content ? 'element_coverage'
            ORDER BY created_at DESC
            LIMIT 100
        """)

        try:
            result = await session.execute(sql)
            rows = result.fetchall()

            for row in rows:
                if row.coverage is None:
                    continue

                if row.coverage < self.COVERAGE_CRITICAL:
                    alert = Alert(
                        alert_id=self._generate_alert_id(AlertType.LOW_COVERAGE, row.model_name),
                        alert_type=AlertType.LOW_COVERAGE,
                        severity=AlertSeverity.CRITICAL,
                        title=f"Critical: Low element coverage for {row.model_name}",
                        message=f"Model {row.model_name} has element coverage of {row.coverage:.1f}%, below critical threshold of {self.COVERAGE_CRITICAL}%",
                        timestamp=datetime.now(timezone.utc),
                        model_name=row.model_name,
                        metrics={"coverage": row.coverage, "unknown": row.unknown or 0},
                    )
                    alerts.append(alert)

                elif row.coverage < self.COVERAGE_WARNING:
                    alert = Alert(
                        alert_id=self._generate_alert_id(AlertType.LOW_COVERAGE, row.model_name),
                        alert_type=AlertType.LOW_COVERAGE,
                        severity=AlertSeverity.WARNING,
                        title=f"Warning: Low element coverage for {row.model_name}",
                        message=f"Model {row.model_name} has element coverage of {row.coverage:.1f}%, below warning threshold of {self.COVERAGE_WARNING}%",
                        timestamp=datetime.now(timezone.utc),
                        model_name=row.model_name,
                        metrics={"coverage": row.coverage, "unknown": row.unknown or 0},
                    )
                    alerts.append(alert)

        except Exception as e:
            logger.warning(f"Failed to check quality alerts: {e}")

        return alerts

    async def check_failure_rate_alerts(
        self,
        session: AsyncSession,
        window_minutes: int = 60,
    ) -> list[Alert]:
        """Check for high failure rate alerts."""
        alerts = []

        # For now, we'll estimate from recent models
        # In production, you'd have a separate serialization_log table
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)

        # Count low-quality models as proxy for failures
        sql = text("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (
                    WHERE (serialized_content->>'element_coverage')::float < 80
                ) as low_quality
            FROM serialized_models
            WHERE created_at > :cutoff
        """)

        try:
            result = await session.execute(sql, {"cutoff": cutoff})
            row = result.fetchone()

            if row and row.total > 10:  # Minimum sample size
                failure_rate = row.low_quality / row.total if row.total > 0 else 0

                if failure_rate >= self.FAILURE_RATE_CRITICAL:
                    alert = Alert(
                        alert_id=self._generate_alert_id(AlertType.HIGH_FAILURE_RATE),
                        alert_type=AlertType.HIGH_FAILURE_RATE,
                        severity=AlertSeverity.CRITICAL,
                        title="Critical: High serialization failure rate",
                        message=f"Failure rate is {failure_rate:.1%} ({row.low_quality}/{row.total} models) in last {window_minutes} minutes",
                        timestamp=datetime.now(timezone.utc),
                        metrics={
                            "failure_rate": failure_rate,
                            "failed": row.low_quality,
                            "total": row.total,
                            "window_minutes": window_minutes,
                        },
                    )
                    alerts.append(alert)

                elif failure_rate >= self.FAILURE_RATE_WARNING:
                    alert = Alert(
                        alert_id=self._generate_alert_id(AlertType.HIGH_FAILURE_RATE),
                        alert_type=AlertType.HIGH_FAILURE_RATE,
                        severity=AlertSeverity.WARNING,
                        title="Warning: Elevated serialization failure rate",
                        message=f"Failure rate is {failure_rate:.1%} ({row.low_quality}/{row.total} models) in last {window_minutes} minutes",
                        timestamp=datetime.now(timezone.utc),
                        metrics={
                            "failure_rate": failure_rate,
                            "failed": row.low_quality,
                            "total": row.total,
                            "window_minutes": window_minutes,
                        },
                    )
                    alerts.append(alert)

        except Exception as e:
            logger.warning(f"Failed to check failure rate alerts: {e}")

        return alerts

    async def check_processing_stall_alerts(
        self,
        session: AsyncSession,
        stall_minutes: int = 15,
    ) -> list[Alert]:
        """Check for processing stalls (no recent activity)."""
        alerts = []

        sql = text("""
            SELECT
                MAX(created_at) as last_serialization,
                COUNT(*) as total_count
            FROM serialized_models
        """)

        try:
            result = await session.execute(sql)
            row = result.fetchone()

            if row and row.last_serialization:
                last_time = row.last_serialization.replace(tzinfo=timezone.utc)
                time_since = (datetime.now(timezone.utc) - last_time).total_seconds() / 60

                # Only alert if we have some models (not empty database)
                if time_since > stall_minutes and row.total_count > 0:
                    alert = Alert(
                        alert_id=self._generate_alert_id(AlertType.PROCESSING_STALL),
                        alert_type=AlertType.PROCESSING_STALL,
                        severity=AlertSeverity.WARNING,
                        title=f"Warning: No serialization activity for {int(time_since)} minutes",
                        message=f"Last model was serialized {int(time_since)} minutes ago. Pipeline may be stalled.",
                        timestamp=datetime.now(timezone.utc),
                        metrics={"minutes_since_last": time_since, "total_models": row.total_count},
                    )
                    alerts.append(alert)

        except Exception as e:
            logger.warning(f"Failed to check processing stall alerts: {e}")

        return alerts

    async def check_all_alerts(
        self,
        session: AsyncSession,
    ) -> list[Alert]:
        """Run all alert checks."""
        all_alerts = []

        # Check all alert types
        all_alerts.extend(await self.check_quality_alerts(session))
        all_alerts.extend(await self.check_failure_rate_alerts(session))
        all_alerts.extend(await self.check_processing_stall_alerts(session))

        # Filter by cooldown
        filtered_alerts = []
        now = datetime.now(timezone.utc)

        for alert in all_alerts:
            last_sent = self._alert_history.get(alert.alert_type)
            if last_sent is None or (now - last_sent).total_seconds() > self.ALERT_COOLDOWN_MINUTES * 60:
                filtered_alerts.append(alert)

        return filtered_alerts

    async def process_alerts(
        self,
        session: AsyncSession,
        send_notifications: bool = True,
    ) -> dict[str, Any]:
        """Check alerts and send notifications."""
        alerts = await self.check_all_alerts(session)

        critical = [a for a in alerts if a.severity == AlertSeverity.CRITICAL]
        warnings = [a for a in alerts if a.severity == AlertSeverity.WARNING]

        result = {
            "total_alerts": len(alerts),
            "critical": len(critical),
            "warnings": len(warnings),
            "alerts_sent": 0,
            "alerts": [a.to_dict() for a in alerts],
        }

        if not alerts:
            return result

        # Store alerts
        for alert in alerts:
            self._alerts[alert.alert_id] = alert

        # Send notifications for critical alerts
        if send_notifications and critical:
            sent = await self.send_email_notifications(critical)
            result["alerts_sent"] = sent

            # Update alert history
            for alert in critical:
                self._alert_history[alert.alert_type] = datetime.now(timezone.utc)
                alert.notification_sent = True

        return result

    async def send_email_notifications(
        self,
        alerts: list[Alert],
    ) -> int:
        """Send email notifications for alerts."""
        if not self.to_emails:
            logger.warning("No recipient emails configured")
            return 0

        if not self.smtp_host:
            logger.warning("SMTP not configured")
            return 0

        sent_count = 0

        try:
            # Build email
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"Serialization Alert: {len(alerts)} alert(s)"
            msg["From"] = self.from_email
            msg["To"] = ", ".join(self.to_emails)

            # HTML body
            html = self._build_email_html(alerts)
            html_part = MIMEText(html, "html")
            msg.attach(html_part)

            # Send
            with SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            sent_count = len(alerts)
            logger.info(f"Sent {sent_count} email notifications")

        except Exception as e:
            logger.error(f"Failed to send email notifications: {e}")

        return sent_count

    def _build_email_html(self, alerts: list[Alert]) -> str:
        """Build HTML email body."""
        critical = [a for a in alerts if a.severity == AlertSeverity.CRITICAL]
        warnings = [a for a in alerts if a.severity == AlertSeverity.WARNING]

        html = """
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; }
                .alert { padding: 10px; margin: 10px 0; border-radius: 4px; }
                .critical { background: #fee; border: 1px solid #c00; }
                .warning { background: #ffc; border: 1px solid #cc0; }
                .timestamp { color: #666; font-size: 0.9em; }
            </style>
        </head>
        <body>
            <h2>Serialization Pipeline Alerts</h2>
            <p>Generated at: """ + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC") + """</p>
        """

        if critical:
            html += f"<h3>Critical Alerts ({len(critical)})</h3>"
            for alert in critical:
                html += f"""
                <div class="alert critical">
                    <strong>{alert.title}</strong><br/>
                    {alert.message}<br/>
                    <span class="timestamp">{alert.timestamp.strftime('%H:%M:%S')}</span>
                </div>
                """

        if warnings:
            html += f"<h3>Warnings ({len(warnings)})</h3>"
            for alert in warnings:
                html += f"""
                <div class="alert warning">
                    <strong>{alert.title}</strong><br/>
                    {alert.message}<br/>
                    <span class="timestamp">{alert.timestamp.strftime('%H:%M:%S')}</span>
                </div>
                """

        html += """
        </body>
        </html>
        """

        return html

    def get_active_alerts(self) -> list[dict[str, Any]]:
        """Get all active (unresolved) alerts."""
        return [
            alert.to_dict()
            for alert in self._alerts.values()
            if not alert.resolved
        ]

    def resolve_alert(self, alert_id: str) -> bool:
        """Mark an alert as resolved."""
        if alert_id in self._alerts:
            self._alerts[alert_id].resolved = True
            self._alerts[alert_id].resolved_at = datetime.now(timezone.utc)
            return True
        return False

    def clear_resolved_alerts(self, older_than_hours: int = 24) -> int:
        """Clear resolved alerts older than specified hours."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
        to_remove = [
            aid for aid, alert in self._alerts.items()
            if alert.resolved and alert.resolved_at and alert.resolved_at < cutoff
        ]

        for aid in to_remove:
            del self._alerts[aid]

        return len(to_remove)


# Global instance
_default_manager: SerializeAlertManager | None = None


def get_alert_manager() -> SerializeAlertManager:
    """Get global alert manager."""
    global _default_manager
    if _default_manager is None:
        _default_manager = SerializeAlertManager()
    return _default_manager
