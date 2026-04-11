"""Text cleaner for normalizing and sanitizing content."""

import re
import unicodedata
from typing import Any

from app.bootstrap.logging import get_logger

logger = get_logger(__name__)


class TextCleaner:
    """Clean and normalize text content.

    Operations:
    - Unicode normalization
    - Whitespace normalization
    - Control character removal
    - URL/email masking (optional)
    - HTML entity decoding
    - Profanity filtering (placeholder)
    """

    # Patterns
    URL_PATTERN = re.compile(
        r"https?://[^\s<>\"']+|www\.[^\s<>\"']+",
        re.IGNORECASE,
    )
    EMAIL_PATTERN = re.compile(
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    )
    WHITESPACE_PATTERN = re.compile(r"[ \t]+")
    NEWLINE_PATTERN = re.compile(r"\n{3,}")
    CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

    def __init__(
        self,
        *,
        normalize_unicode: bool = True,
        normalize_whitespace: bool = True,
        remove_control_chars: bool = True,
        mask_urls: bool = False,
        mask_emails: bool = False,
        max_length: int | None = None,
    ) -> None:
        """Initialize TextCleaner with options.

        Args:
            normalize_unicode: Apply NFKC normalization.
            normalize_whitespace: Collapse multiple spaces/newlines.
            remove_control_chars: Remove non-printable control characters.
            mask_urls: Replace URLs with [URL].
            mask_emails: Replace emails with [EMAIL].
            max_length: Truncate text to max length.
        """
        self._normalize_unicode = normalize_unicode
        self._normalize_whitespace = normalize_whitespace
        self._remove_control_chars = remove_control_chars
        self._mask_urls = mask_urls
        self._mask_emails = mask_emails
        self._max_length = max_length

    def clean(self, text: str) -> str:
        """Apply all configured cleaning operations.

        Args:
            text: Input text to clean.

        Returns:
            Cleaned text.
        """
        if not text:
            return ""

        result = text

        # Unicode normalization
        if self._normalize_unicode:
            result = self._apply_unicode_normalization(result)

        # Remove control characters
        if self._remove_control_chars:
            result = self._apply_control_char_removal(result)

        # Mask URLs
        if self._mask_urls:
            result = self._apply_url_masking(result)

        # Mask emails
        if self._mask_emails:
            result = self._apply_email_masking(result)

        # Normalize whitespace
        if self._normalize_whitespace:
            result = self._apply_whitespace_normalization(result)

        # Truncate
        if self._max_length and len(result) > self._max_length:
            result = result[: self._max_length]

        return result.strip()

    def _apply_unicode_normalization(self, text: str) -> str:
        """Apply NFKC unicode normalization."""
        return unicodedata.normalize("NFKC", text)

    def _apply_control_char_removal(self, text: str) -> str:
        """Remove control characters except newlines and tabs."""
        return self.CONTROL_CHAR_PATTERN.sub("", text)

    def _apply_url_masking(self, text: str) -> str:
        """Replace URLs with [URL]."""
        return self.URL_PATTERN.sub("[URL]", text)

    def _apply_email_masking(self, text: str) -> str:
        """Replace emails with [EMAIL]."""
        return self.EMAIL_PATTERN.sub("[EMAIL]", text)

    def _apply_whitespace_normalization(self, text: str) -> str:
        """Normalize whitespace."""
        # Collapse multiple spaces to single space
        result = self.WHITESPACE_PATTERN.sub(" ", text)
        # Collapse multiple newlines to double newline
        result = self.NEWLINE_PATTERN.sub("\n\n", result)
        return result


class TitleCleaner:
    """Clean and normalize titles."""

    # Common title suffixes to remove
    SITE_SUFFIXES = [
        " - ",
        " | ",
        " :: ",
        " » ",
        " — ",
    ]

    def __init__(
        self,
        *,
        remove_site_name: bool = True,
        max_length: int = 200,
        capitalize: bool = False,
    ) -> None:
        """Initialize TitleCleaner.

        Args:
            remove_site_name: Remove site name suffixes.
            max_length: Maximum title length.
            capitalize: Capitalize first letter.
        """
        self._remove_site_name = remove_site_name
        self._max_length = max_length
        self._capitalize = capitalize

    def clean(self, title: str) -> str:
        """Clean a title string.

        Args:
            title: Input title.

        Returns:
            Cleaned title.
        """
        if not title:
            return ""

        result = title.strip()

        # Remove site name suffixes
        if self._remove_site_name:
            result = self._remove_suffix(result)

        # Normalize whitespace
        result = " ".join(result.split())

        # Truncate
        if len(result) > self._max_length:
            result = result[: self._max_length - 3] + "..."

        # Capitalize
        if self._capitalize and result:
            result = result[0].upper() + result[1:]

        return result

    def _remove_suffix(self, title: str) -> str:
        """Remove common site name suffixes."""
        for suffix in self.SITE_SUFFIXES:
            idx = title.rfind(suffix)
            if idx > len(title) // 3:  # Only if suffix is in latter part
                title = title[:idx]
        return title


# Default instances
default_text_cleaner = TextCleaner()
default_title_cleaner = TitleCleaner()


def clean_text(text: str) -> str:
    """Clean text using default cleaner."""
    return default_text_cleaner.clean(text)


def clean_title(title: str) -> str:
    """Clean title using default cleaner."""
    return default_title_cleaner.clean(title)
