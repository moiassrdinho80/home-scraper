"""
Email sending via SMTP.
"""

import logging
import smtplib
import uuid
from datetime import datetime
from email.mime.text import MIMEText
from typing import List, Dict

from config import Config

logger = logging.getLogger(__name__)


class EmailError(Exception):
    """Custom exception for email errors."""
    pass


def format_email_body(listings: List[Dict[str, str]]) -> str:
    """
    Format listings as a plain text numbered list.
    
    Args:
        listings: List of listing dictionaries
        
    Returns:
        Formatted email body as string
    """
    if not listings:
        return "No new listings found."
    
    lines = []
    for i, listing in enumerate(listings, start=1):
        # Title with status
        title_line = f"{i}) {listing.get('title', 'Unknown')}"
        status = listing.get('status', '').strip()
        if status:
            title_line += f" ({status})"
        lines.append(title_line)
        
        # Price
        price = listing.get('price', '').strip()
        if price:
            lines.append(f"   Price: {price}")
        
        # Location
        location = listing.get('location', '').strip()
        if location:
            lines.append(f"   Location: {location}")
        
        # Details
        details = listing.get('details_text', '').strip()
        if details:
            for detail_line in details.split('\n'):
                if detail_line.strip():
                    lines.append(f"   {detail_line}")
        
        # URL
        url = listing.get('url', '').strip()
        if url:
            lines.append(f"   Link: {url}")
        
        # Blank line between listings
        if i < len(listings):
            lines.append("")
    
    return "\n".join(lines)


def send_email(config: Config, listings: List[Dict[str, str]]) -> None:
    """
    Send email with listings via SMTP.
    Supports multiple recipients (comma-separated).
    Always sends an email, even if no listings (sends "no new listings" message).
    
    Args:
        config: Configuration instance
        listings: List of listing dictionaries to include (can be empty)
        
    Raises:
        EmailError: If email sending fails
    """
    
    try:
        # Format email
        if listings:
            subject = f"{config.EMAIL_SUBJECT_PREFIX}: New listings ({len(listings)})"
            body = format_email_body(listings)
        else:
            subject = f"{config.EMAIL_SUBJECT_PREFIX}: Daily Update"
            body = "AHLAN AHLAN!!! There are no new listings today Sadly:("
        
        # Ensure body is not empty
        if not body or not body.strip():
            body = "AHLAN AHLAN!!! There are no new listings today Sadly:("
            logger.warning("Email body was empty, using default message")
        
        # Log the body for debugging
        logger.debug(f"Email body length: {len(body)}, preview: {body[:100]}")
        
        # Parse recipients (support comma-separated list)
        recipients = [email.strip() for email in config.EMAIL_TO.split(",") if email.strip()]
        if not recipients:
            raise EmailError("No valid email recipients found in EMAIL_TO")
        
        # Create message
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = config.EMAIL_FROM
        msg["To"] = ", ".join(recipients)  # For display in email headers
        
        # Generate unique Message-ID to create new thread (not reply to previous)
        # Format: <timestamp-uuid@domain>
        domain = config.EMAIL_FROM.split("@")[-1] if "@" in config.EMAIL_FROM else "fairfax-fthb.local"
        unique_id = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
        msg["Message-ID"] = f"<{unique_id}@{domain}>"
        
        # Remove In-Reply-To and References headers to prevent threading
        if "In-Reply-To" in msg:
            del msg["In-Reply-To"]
        if "References" in msg:
            del msg["References"]
        
        # Send via SMTP
        logger.info(f"Connecting to SMTP server {config.SMTP_HOST}:{config.SMTP_PORT}")
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=30) as server:
            server.starttls()
            server.login(config.SMTP_USER, config.SMTP_PASS)
            # Send to all recipients
            server.send_message(msg, to_addrs=recipients)
        
        if listings:
            logger.info(f"Successfully sent email to {len(recipients)} recipient(s): {', '.join(recipients)} with {len(listings)} listings")
        else:
            logger.info(f"Successfully sent email to {len(recipients)} recipient(s): {', '.join(recipients)} - No new listings today")
        
    except smtplib.SMTPException as e:
        raise EmailError(f"SMTP error: {e}")
    except Exception as e:
        raise EmailError(f"Unexpected error sending email: {e}")

