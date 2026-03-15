"""Email configuration (Brevo API).

Manages Brevo API credentials and email settings for automated reports.
"""

import os


class EmailConfig:
    """Configuration for email notifications via Brevo API.

    Attributes:
        api_key: Brevo API key (format: xkeysib-...)
        email_to: Recipient email address
        email_from: Sender email address (must be verified in Brevo)
        email_from_name: Sender display name

    Examples:
        >>> config = get_email_config()
        >>> if config.is_configured():
        ...     print(f"Email configured for {config.email_to}")
        ... else:
        ...     print("Email not configured")
    """

    def __init__(self):
        """Initialize email configuration from environment variables."""
        self.api_key = os.getenv("BREVO_API_KEY")
        self.email_to = os.getenv("EMAIL_TO")
        self.email_from = os.getenv("EMAIL_FROM")
        self.email_from_name = os.getenv("EMAIL_FROM_NAME", "Training Logs")

    def is_configured(self) -> bool:
        """Check if email is properly configured.

        Returns:
            True if all required settings are present

        Examples:
            >>> config = get_email_config()
            >>> if config.is_configured():
            ...     pass
            ... else:
            ...     pass
        """
        return bool(self.api_key and self.email_to and self.email_from)

    def get_missing_vars(self) -> list[str]:
        """Get list of missing required environment variables.

        Returns:
            List of missing variable names

        Examples:
            >>> config = get_email_config()
            >>> missing = config.get_missing_vars()
            >>> if missing:
            ...     print(f"Missing: {', '.join(missing)}")
        """
        missing = []
        if not self.api_key:
            missing.append("BREVO_API_KEY")
        if not self.email_to:
            missing.append("EMAIL_TO")
        if not self.email_from:
            missing.append("EMAIL_FROM")
        return missing


# Global Email config instance
_email_config_instance: EmailConfig | None = None


def get_email_config() -> EmailConfig:
    """Get singleton instance of Email config.

    Returns:
        EmailConfig instance

    Examples:
        >>> config = get_email_config()
        >>> if config.is_configured():
        ...     print("Email ready")
    """
    global _email_config_instance

    if _email_config_instance is None:
        _email_config_instance = EmailConfig()
    return _email_config_instance


def reset_email_config():
    """Reset Email config singleton (useful for tests).

    Examples:
        >>> reset_email_config()
        >>> config = get_email_config()  # Creates new instance
    """
    global _email_config_instance
    _email_config_instance = None
