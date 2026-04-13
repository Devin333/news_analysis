"""Prompt registry for managing prompt templates.

This module provides versioned prompt template management.
"""

from pathlib import Path
from typing import Any

from app.bootstrap.logging import get_logger

logger = get_logger(__name__)

# Base path for prompt templates
TEMPLATES_DIR = Path(__file__).parent / "templates"


class PromptRegistry:
    """Registry for prompt templates.

    Manages versioned prompt templates loaded from files or registered programmatically.
    """

    def __init__(self) -> None:
        """Initialize the registry."""
        self._templates: dict[str, dict[str, str]] = {}  # key -> version -> template
        self._load_templates()

    def _load_templates(self) -> None:
        """Load templates from templates directory."""
        if not TEMPLATES_DIR.exists():
            logger.warning(f"Templates directory not found: {TEMPLATES_DIR}")
            return

        for template_file in TEMPLATES_DIR.glob("*.md"):
            # Parse filename: {key}_{version}.md
            name = template_file.stem
            parts = name.rsplit("_", 1)

            if len(parts) == 2:
                key, version = parts
            else:
                key = name
                version = "v1"

            content = template_file.read_text(encoding="utf-8")
            self.register(key, content, version=version)

        logger.info(f"Loaded {len(self._templates)} prompt templates")

    def register(
        self,
        key: str,
        template: str,
        *,
        version: str = "v1",
    ) -> None:
        """Register a prompt template.

        Args:
            key: Template key.
            template: Template content.
            version: Template version.
        """
        if key not in self._templates:
            self._templates[key] = {}

        self._templates[key][version] = template
        logger.debug(f"Registered prompt template: {key} ({version})")

    def get(
        self,
        key: str,
        *,
        version: str | None = None,
        variables: dict[str, Any] | None = None,
    ) -> str | None:
        """Get a prompt template.

        Args:
            key: Template key.
            version: Optional version (defaults to latest).
            variables: Optional variables to substitute.

        Returns:
            Template content or None if not found.
        """
        if key not in self._templates:
            logger.warning(f"Prompt template not found: {key}")
            return None

        versions = self._templates[key]

        if version:
            template = versions.get(version)
        else:
            # Get latest version
            sorted_versions = sorted(versions.keys(), reverse=True)
            template = versions.get(sorted_versions[0]) if sorted_versions else None

        if template is None:
            logger.warning(f"Prompt template version not found: {key} ({version})")
            return None

        # Substitute variables if provided
        if variables:
            try:
                template = template.format(**variables)
            except KeyError as e:
                logger.warning(f"Missing variable in template {key}: {e}")

        return template

    def list_keys(self) -> list[str]:
        """List all template keys.

        Returns:
            List of template keys.
        """
        return list(self._templates.keys())

    def list_versions(self, key: str) -> list[str]:
        """List versions for a template.

        Args:
            key: Template key.

        Returns:
            List of versions.
        """
        if key not in self._templates:
            return []
        return list(self._templates[key].keys())

    def has(self, key: str, version: str | None = None) -> bool:
        """Check if template exists.

        Args:
            key: Template key.
            version: Optional version.

        Returns:
            True if template exists.
        """
        if key not in self._templates:
            return False
        if version:
            return version in self._templates[key]
        return True


# Global registry instance
_registry: PromptRegistry | None = None


def get_registry() -> PromptRegistry:
    """Get the global prompt registry.

    Returns:
        The global PromptRegistry instance.
    """
    global _registry
    if _registry is None:
        _registry = PromptRegistry()
    return _registry


def get_prompt(
    key: str,
    *,
    version: str | None = None,
    variables: dict[str, Any] | None = None,
) -> str | None:
    """Get a prompt template.

    Convenience function for get_registry().get().

    Args:
        key: Template key.
        version: Optional version.
        variables: Optional variables.

    Returns:
        Template content or None.
    """
    return get_registry().get(key, version=version, variables=variables)


def register_prompt(
    key: str,
    template: str,
    *,
    version: str = "v1",
) -> None:
    """Register a prompt template.

    Convenience function for get_registry().register().

    Args:
        key: Template key.
        template: Template content.
        version: Template version.
    """
    get_registry().register(key, template, version=version)
