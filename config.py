"""
Configuration management from environment variables.
"""

import os
import logging
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

logger = logging.getLogger(__name__)


class Config:
    """Configuration loaded from environment variables."""
    
    # SMTP settings
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASS: str
    
    # Email settings
    EMAIL_FROM: str
    EMAIL_TO: str
    EMAIL_SUBJECT_PREFIX: str = "Fairfax FTHB"
    ALWAYS_EMAIL: bool = False
    
    # Database path
    DB_PATH: str = "listings.db"
    
    @classmethod
    def load(cls) -> "Config":
        """
        Load configuration from environment variables.
        Automatically loads from .env file if present and python-dotenv is installed.
        
        Returns:
            Config instance
            
        Raises:
            ValueError: If required environment variables are missing
        """
        # Try to load .env file if python-dotenv is available
        if load_dotenv is not None:
            env_path = Path(__file__).parent / ".env"
            if env_path.exists():
                load_dotenv(env_path)
                logger.debug(f"Loaded environment variables from {env_path}")
            else:
                logger.debug("No .env file found, using system environment variables")
        
        config = cls()
        
        # SMTP settings (required)
        config.SMTP_HOST = os.getenv("SMTP_HOST", "")
        config.SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
        config.SMTP_USER = os.getenv("SMTP_USER", "")
        config.SMTP_PASS = os.getenv("SMTP_PASS", "")
        
        # Email settings (required)
        config.EMAIL_FROM = os.getenv("EMAIL_FROM", "")
        config.EMAIL_TO = os.getenv("EMAIL_TO", "")
        config.EMAIL_SUBJECT_PREFIX = os.getenv("EMAIL_SUBJECT_PREFIX", "Fairfax FTHB")
        
        # Optional settings
        config.ALWAYS_EMAIL = os.getenv("ALWAYS_EMAIL", "false").lower() in ("true", "1", "yes")
        config.DB_PATH = os.getenv("DB_PATH", "listings.db")
        
        # Validate required settings
        required = {
            "SMTP_HOST": config.SMTP_HOST,
            "SMTP_USER": config.SMTP_USER,
            "SMTP_PASS": config.SMTP_PASS,
            "EMAIL_FROM": config.EMAIL_FROM,
            "EMAIL_TO": config.EMAIL_TO,
        }
        
        missing = [key for key, value in required.items() if not value]
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                f"Please set these in your environment or .env file."
            )
        
        logger.debug("Configuration loaded successfully")
        return config

