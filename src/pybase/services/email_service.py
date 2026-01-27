"""Email service for sending emails with attachments."""

import logging
import os
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Optional
from smtplib import SMTPException

logger = logging.getLogger(__name__)


# =============================================================================
# Email Service
# =============================================================================


class EmailService:
    """Service for sending emails with attachments."""

    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        smtp_from_email: Optional[str] = None,
        smtp_from_name: Optional[str] = None,
        smtp_tls: Optional[bool] = None,
    ):
        """Initialize email service with SMTP configuration.

        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port (default: 587)
            smtp_user: SMTP username for authentication
            smtp_password: SMTP password for authentication
            smtp_from_email: From email address (default: noreply@pybase.dev)
            smtp_from_name: From display name (default: PyBase)
            smtp_tls: Use TLS encryption (default: True)
        """
        # Load from environment if not provided
        self.smtp_host = smtp_host or os.getenv("SMTP_HOST")
        self.smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = smtp_user or os.getenv("SMTP_USER")
        self.smtp_password = smtp_password or os.getenv("SMTP_PASSWORD")
        self.smtp_from_email = smtp_from_email or os.getenv(
            "SMTP_FROM_EMAIL", "noreply@pybase.dev"
        )
        self.smtp_from_name = smtp_from_name or os.getenv("SMTP_FROM_NAME", "PyBase")
        self.smtp_tls = smtp_tls if smtp_tls is not None else os.getenv(
            "SMTP_TLS", "True"
        ).lower() in ("true", "1", "yes")

    # -------------------------------------------------------------------------
    # Configuration Validation
    # -------------------------------------------------------------------------

    def is_configured(self) -> bool:
        """Check if SMTP configuration is available.

        Returns:
            True if SMTP is properly configured
        """
        return bool(self.smtp_host and self.smtp_user)

    # -------------------------------------------------------------------------
    # Email Sending
    # -------------------------------------------------------------------------

    def send_email(
        self,
        to: list[str] | str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        attachments: Optional[list[dict[str, Any]]] = None,
        cc: Optional[list[str] | str] = None,
        bcc: Optional[list[str]] = None,
        reply_to: Optional[str] = None,
    ) -> dict[str, Any]:
        """Send an email with optional attachments.

        Args:
            to: Recipient email address(es)
            subject: Email subject line
            body: Plain text email body
            html_body: Optional HTML email body
            attachments: List of attachments with keys:
                - filename: str
                - content: bytes
                - mimetype: str (optional)
            cc: CC recipient email address(es)
            bcc: BCC recipient email address(es)
            reply_to: Reply-to email address

        Returns:
            dict with keys:
                - success: bool
                - message: str
                - recipients_count: int
                - error: str (if failed)

        Raises:
            ValueError: If SMTP is not configured or recipients invalid
            SMTPException: If sending fails
        """
        # Validate configuration
        if not self.is_configured():
            raise ValueError("SMTP configuration not available")

        # Normalize recipients to lists
        to_list = [to] if isinstance(to, str) else to
        if not to_list:
            raise ValueError("At least one recipient is required")

        cc_list = [cc] if isinstance(cc, str) else (cc or [])
        bcc_list = bcc or []

        # Create email message
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = f"{self.smtp_from_name} <{self.smtp_from_email}>"
        msg["To"] = ", ".join(to_list)

        if cc_list:
            msg["Cc"] = ", ".join(cc_list)

        if reply_to:
            msg["Reply-To"] = reply_to

        # Add message body
        if html_body:
            # Multipart alternative: plain text and HTML
            from email.mime_alternative import MIMEMultipartAlternative

            alt_msg = MIMEMultipartAlternative()
            alt_msg.attach(MIMEText(body, "plain", _charset="utf-8"))
            alt_msg.attach(MIMEText(html_body, "html", _charset="utf-8"))
            msg.attach(alt_msg)
        else:
            msg.attach(MIMEText(body, "plain", _charset="utf-8"))

        # Attach files
        if attachments:
            for attachment in attachments:
                filename = attachment.get("filename")
                content = attachment.get("content")
                mimetype = attachment.get(" mimetype", "application/octet-stream")

                if not filename or not content:
                    logger.warning(f"Skipping invalid attachment: {attachment}")
                    continue

                part = MIMEApplication(content)
                part.add_header(
                    "Content-Disposition", "attachment", filename=filename
                )
                if mimetype and mimetype != "application/octet-stream":
                    part.set_type(mimetype)
                msg.attach(part)

        # All recipients (including BCC)
        all_recipients = to_list + cc_list + bcc_list

        # Send email
        try:
            import smtplib

            logger.info(
                f"Sending email to {len(all_recipients)} recipients: {subject[:50]}"
            )

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_tls:
                    server.starttls()

                if self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)

                server.send_message(msg, to_addrs=all_recipients)

            logger.info(f"Email sent successfully to {len(all_recipients)} recipients")

            return {
                "success": True,
                "message": "Email sent successfully",
                "recipients_count": len(all_recipients),
            }

        except SMTPException as e:
            logger.error(f"SMTP error sending email: {e}")
            return {
                "success": False,
                "message": "Failed to send email",
                "error": str(e),
                "recipients_count": 0,
            }
        except Exception as e:
            logger.error(f"Unexpected error sending email: {e}", exc_info=True)
            return {
                "success": False,
                "message": "Failed to send email",
                "error": str(e),
                "recipients_count": 0,
            }

    def send_email_with_file_attachment(
        self,
        to: list[str] | str,
        subject: str,
        body: str,
        file_path: str,
        attachment_filename: Optional[str] = None,
        html_body: Optional[str] = None,
        cc: Optional[list[str] | str] = None,
        bcc: Optional[list[str]] = None,
        reply_to: Optional[str] = None,
    ) -> dict[str, Any]:
        """Send an email with a file attachment from disk.

        Args:
            to: Recipient email address(es)
            subject: Email subject line
            body: Plain text email body
            file_path: Path to file to attach
            attachment_filename: Custom attachment filename (default: basename of file_path)
            html_body: Optional HTML email body
            cc: CC recipient email address(es)
            bcc: BCC recipient email address(es)
            reply_to: Reply-to email address

        Returns:
            dict with send results

        Raises:
            FileNotFoundError: If file_path does not exist
            ValueError: If SMTP is not configured or recipients invalid
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Attachment file not found: {file_path}")

        # Read file content
        with open(file_path, "rb") as f:
            content = f.read()

        # Determine filename
        filename = attachment_filename or os.path.basename(file_path)

        # Determine mimetype based on extension
        mimetype = self._get_mimetype(filename)

        # Send email
        return self.send_email(
            to=to,
            subject=subject,
            body=body,
            html_body=html_body,
            attachments=[{"filename": filename, "content": content, "mimetype": mimetype}],
            cc=cc,
            bcc=bcc,
            reply_to=reply_to,
        )

    def send_report_email(
        self,
        to: list[str] | str,
        subject: str,
        report_name: str,
        file_path: str,
        message: Optional[str] = None,
        html_message: Optional[str] = None,
        cc: Optional[list[str] | str] = None,
        bcc: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Send a report via email with attachment.

        Convenience method for sending reports with standard formatting.

        Args:
            to: Recipient email address(es)
            subject: Email subject (default: "Report: {report_name}")
            report_name: Name of the report
            file_path: Path to report file (PDF, etc.)
            message: Optional custom message (default: standard message)
            html_message: Optional HTML message
            cc: CC recipient email address(es)
            bcc: BCC recipient email address(es)

        Returns:
            dict with send results
        """
        # Default subject
        if not subject:
            subject = f"Report: {report_name}"

        # Default message
        if not message and not html_message:
            message = (
                f"Please find the attached report: {report_name}.\n\n"
                f"This report was generated on {self._get_current_date()}."
            )

        return self.send_email_with_file_attachment(
            to=to,
            subject=subject,
            body=message or "Please find the attached report.",
            html_body=html_message,
            file_path=file_path,
            cc=cc,
            bcc=bcc,
        )

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    @staticmethod
    def _get_mimetype(filename: str) -> str:
        """Get MIME type for a filename based on extension.

        Args:
            filename: Filename to check

        Returns:
            MIME type string
        """
        import mimetypes

        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or "application/octet-stream"

    @staticmethod
    def _get_current_date() -> str:
        """Get current date formatted for email messages.

        Returns:
            Formatted date string
        """
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # -------------------------------------------------------------------------
    # Template Methods
    # -------------------------------------------------------------------------

    def render_email_template(
        self,
        template: str,
        context: dict[str, Any],
    ) -> str:
        """Render an email template with context variables.

        Supports simple {{variable}} substitution.

        Args:
            template: Template string with {{variable}} placeholders
            context: Dictionary of variables to substitute

        Returns:
            Rendered template string
        """
        import re

        pattern = re.compile(r"\{\{([^}]+)\}\}")

        def replace(match: re.Match) -> str:
            var_path = match.group(1).strip()
            value = self._get_nested_value(var_path, context)
            return str(value) if value is not None else ""

        return pattern.sub(replace, template)

    @staticmethod
    def _get_nested_value(path: str, context: dict[str, Any]) -> Any:
        """Get value from nested dictionary using dot notation.

        Args:
            path: Dot-separated path (e.g., "user.name")
            context: Context dictionary

        Returns:
            Value at path or None
        """
        parts = path.split(".")
        value = context

        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            elif hasattr(value, part):
                value = getattr(value, part)
            else:
                return None

            if value is None:
                return None

        return value


# =============================================================================
# Dependency Injection
# =============================================================================


def get_email_service() -> EmailService:
    """Get email service instance with default configuration.

    Loads configuration from environment variables.

    Returns:
        EmailService instance
    """
    return EmailService()
