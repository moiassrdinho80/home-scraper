"""
Email sending via SMTP.
"""

import logging
import smtplib
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
    
    Args:
        config: Configuration instance
        listings: List of listing dictionaries to include
        
    Raises:
        EmailError: If email sending fails
    """
    if not listings:
        logger.warning("No listings to email")
        return
    
    try:
        # Format email
        subject = f"{config.EMAIL_SUBJECT_PREFIX}: New listings ({len(listings)})"
        body = format_email_body(listings)
        
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = config.EMAIL_FROM
        msg["To"] = config.EMAIL_TO
        
        # Send via SMTP
        logger.info(f"Connecting to SMTP server {config.SMTP_HOST}:{config.SMTP_PORT}")
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=30) as server:
            server.starttls()
            server.login(config.SMTP_USER, config.SMTP_PASS)
            server.send_message(msg)
        
        logger.info(f"Successfully sent email to {config.EMAIL_TO} with {len(listings)} listings")
        
    except smtplib.SMTPException as e:
        raise EmailError(f"SMTP error: {e}")
    except Exception as e:
        raise EmailError(f"Unexpected error sending email: {e}")

