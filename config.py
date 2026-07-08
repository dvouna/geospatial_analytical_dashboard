"""
Environment Configuration Module
Handles loading and validating environment variables
"""

import os
from dotenv import load_dotenv
from pathlib import Path
from typing import Optional
import streamlit as st

# Load environment variables from .env file
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)


class Config:
    """Configuration management for the application"""

    # Gemini API Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # Streamlit Configuration
    STREAMLIT_SERVER_PORT: int = int(os.getenv("STREAMLIT_SERVER_PORT", 8501))
    STREAMLIT_SERVER_ADDRESS: str = os.getenv("STREAMLIT_SERVER_ADDRESS", "localhost")
    STREAMLIT_SERVER_BASE_URL_PATH: str = os.getenv(
        "STREAMLIT_SERVER_BASE_URL_PATH", "/"
    )

    # Application Configuration
    APP_NAME: str = "Data Visualization & AI Query Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Data Configuration
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", 100))
    DATA_DIR: str = os.getenv("DATA_DIR", "data")

    # AI Configuration
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    GEMINI_MAX_TOKENS: int = int(os.getenv("GEMINI_MAX_TOKENS", 2048))
    GEMINI_TEMPERATURE: float = float(os.getenv("GEMINI_TEMPERATURE", 0.7))

    # WordPress Integration (deployment only)
    WORDPRESS_DOMAIN: Optional[str] = os.getenv("WORDPRESS_DOMAIN", None)
    STREAMLIT_DOMAIN: Optional[str] = os.getenv("STREAMLIT_DOMAIN", None)

    @classmethod
    def validate(cls) -> tuple[bool, list[str]]:
        """
        Validate required configuration

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check required variables
        if not cls.GEMINI_API_KEY:
            errors.append("GEMINI_API_KEY is not set (optional for demo mode)")

        # Check numeric values
        try:
            if cls.STREAMLIT_SERVER_PORT < 1 or cls.STREAMLIT_SERVER_PORT > 65535:
                errors.append(
                    f"Invalid STREAMLIT_SERVER_PORT: {cls.STREAMLIT_SERVER_PORT}"
                )
        except (ValueError, TypeError):
            errors.append("STREAMLIT_SERVER_PORT must be a valid integer")

        # Check data directory exists
        if not os.path.exists(cls.DATA_DIR):
            try:
                os.makedirs(cls.DATA_DIR, exist_ok=True)
            except Exception as e:
                errors.append(f"Could not create DATA_DIR: {str(e)}")

        return (len(errors) == 0, errors)

    @classmethod
    def get_all_config(cls) -> dict:
        """Get all configuration as a dictionary"""
        return {
            "APP_NAME": cls.APP_NAME,
            "APP_VERSION": cls.APP_VERSION,
            "DEBUG": cls.DEBUG,
            "STREAMLIT_SERVER_PORT": cls.STREAMLIT_SERVER_PORT,
            "STREAMLIT_SERVER_ADDRESS": cls.STREAMLIT_SERVER_ADDRESS,
            "GEMINI_MODEL": cls.GEMINI_MODEL,
            "GEMINI_MAX_TOKENS": cls.GEMINI_MAX_TOKENS,
            "GEMINI_TEMPERATURE": cls.GEMINI_TEMPERATURE,
            "MAX_UPLOAD_SIZE_MB": cls.MAX_UPLOAD_SIZE_MB,
            "DATA_DIR": cls.DATA_DIR,
        }

    @classmethod
    def get_safe_config(cls) -> dict:
        """Get configuration without sensitive data"""
        config = cls.get_all_config()
        # Remove sensitive data
        config.pop("GEMINI_API_KEY", None)
        return config


@st.cache_resource
def get_config() -> Config:
    """Get cached config instance"""
    return Config


def check_environment():
    """Check and validate environment on app startup"""
    is_valid, errors = Config.validate()

    if errors:
        if Config.DEBUG:
            st.warning(
                "⚠️ Configuration warnings:\n" + "\n".join(f"• {e}" for e in errors)
            )
