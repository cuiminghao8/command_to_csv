from __future__ import annotations

import logging
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Iterable, List, Optional

from .config import EmailConfig

logger = logging.getLogger(__name__)


def send_email(
    cfg: EmailConfig,
    body: str,
    attachments: Iterable[str] = (),
    subject: Optional[str] = None,
) -> bool:
    """Send an email with optional file attachments.

    Returns True on success, False on failure (errors are logged, never raised).
    """
    if not cfg.enabled:
        logger.debug("Email disabled; skipping")
        return False
    if not cfg.smtp_server or not cfg.sender or not cfg.recipients:
        logger.warning("Email config incomplete (smtp_server/sender/recipients); skipping")
        return False

    msg = MIMEMultipart()
    msg["Subject"] = subject or cfg.subject
    msg["From"] = cfg.sender
    msg["To"] = ", ".join(cfg.recipients)
    msg.attach(MIMEText(body, "plain", "utf-8"))

    missing: List[str] = []
    for path_str in attachments:
        p = Path(path_str)
        if not p.is_file():
            missing.append(path_str)
            continue
        with p.open("rb") as f:
            part = MIMEApplication(f.read())
        part.add_header("Content-Disposition", "attachment", filename=p.name)
        msg.attach(part)
    if missing:
        logger.warning("Skipping missing attachments: %s", ", ".join(missing))

    try:
        with smtplib.SMTP(cfg.smtp_server, cfg.smtp_port, timeout=30) as smtp:
            smtp.ehlo()
            if cfg.use_tls:
                smtp.starttls()
                smtp.ehlo()
            if cfg.username and cfg.password:
                smtp.login(cfg.username, cfg.password)
            smtp.sendmail(cfg.sender, cfg.recipients, msg.as_string())
    except Exception as exc:
        logger.error("Failed to send email: %s", exc)
        return False

    logger.info("Sent email to %s", ", ".join(cfg.recipients))
    return True
