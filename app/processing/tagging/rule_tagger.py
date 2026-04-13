"""Rule-based tagger for content tagging.

This module provides rule-based tagging using keyword dictionaries
to identify companies, frameworks, models, tasks, and domains.
"""

import re
from dataclasses import dataclass, field

from app.bootstrap.logging import get_logger
from app.contracts.dto.tag import TagMatchDTO, TagType
from app.processing.tagging.dictionaries import get_all_patterns

logger = get_logger(__name__)


@dataclass
class TaggerConfig:
    """Configuration for rule-based tagger."""

    # Minimum confidence for a match
    min_confidence: float = 0.5

    # Whether to match case-insensitively
    case_insensitive: bool = True

    # Whether to require word boundaries
    word_boundary: bool = True

    # Maximum tags per type
    max_tags_per_type: int = 10

    # Confidence boost for title matches
    title_boost: float = 0.2

    # Confidence boost for exact matches
    exact_match_boost: float = 0.1


@dataclass
class TaggingContext:
    """Context for tagging operation."""

    title: str = ""
    excerpt: str = ""
    clean_text: str = ""
    source_type: str | None = None
    content_type: str | None = None


@dataclass
class RuleTaggingResult:
    """Result of rule-based tagging."""

    matches: list[TagMatchDTO] = field(default_factory=list)
    processing_time_ms: float = 0.0
    patterns_checked: int = 0


class RuleTagger:
    """Rule-based tagger using keyword dictionaries.

    Identifies tags by matching patterns against content text.
    Supports multiple tag types: company, framework, model, task, domain.
    """

    def __init__(self, config: TaggerConfig | None = None) -> None:
        """Initialize the tagger.

        Args:
            config: Configuration for tagging behavior.
        """
        self._config = config or TaggerConfig()
        self._patterns = get_all_patterns()
        self._compiled_patterns: dict[str, list[tuple[re.Pattern, str, str]]] = {}
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for efficient matching."""
        for tag_type, patterns in self._patterns.items():
            compiled: list[tuple[re.Pattern, str, str]] = []
            for pattern_text, normalized_name, display_name in patterns:
                # Escape special regex characters
                escaped = re.escape(pattern_text)

                # Add word boundaries if configured
                if self._config.word_boundary:
                    regex_pattern = rf"\b{escaped}\b"
                else:
                    regex_pattern = escaped

                # Compile with case insensitivity if configured
                flags = re.IGNORECASE if self._config.case_insensitive else 0
                try:
                    compiled_re = re.compile(regex_pattern, flags)
                    compiled.append((compiled_re, normalized_name, display_name))
                except re.error as e:
                    logger.warning(f"Failed to compile pattern '{pattern_text}': {e}")

            self._compiled_patterns[tag_type] = compiled

        total_patterns = sum(len(p) for p in self._compiled_patterns.values())
        logger.info(f"Compiled {total_patterns} tagging patterns across {len(self._compiled_patterns)} types")

    def tag(self, context: TaggingContext) -> RuleTaggingResult:
        """Tag content based on context.

        Args:
            context: The tagging context with text fields.

        Returns:
            RuleTaggingResult with matched tags.
        """
        import time

        start_time = time.perf_counter()
        patterns_checked = 0

        # Combine text fields for matching
        title_lower = context.title.lower()
        full_text = f"{context.title} {context.excerpt} {context.clean_text}".lower()

        # Track matches by (tag_type, normalized_name) to avoid duplicates
        matches_map: dict[tuple[str, str], TagMatchDTO] = {}

        for tag_type, patterns in self._compiled_patterns.items():
            type_matches: list[TagMatchDTO] = []

            for compiled_re, normalized_name, display_name in patterns:
                patterns_checked += 1

                # Check for match in full text
                match = compiled_re.search(full_text)
                if match:
                    # Calculate confidence
                    confidence = self._calculate_confidence(
                        match=match,
                        pattern_text=compiled_re.pattern,
                        title_lower=title_lower,
                        normalized_name=normalized_name,
                    )

                    if confidence >= self._config.min_confidence:
                        key = (tag_type, normalized_name)
                        existing = matches_map.get(key)

                        # Keep higher confidence match
                        if existing is None or confidence > existing.confidence:
                            matches_map[key] = TagMatchDTO(
                                tag_id=0,  # Will be resolved by tag service
                                tag_name=display_name,
                                tag_type=TagType(tag_type),
                                confidence=confidence,
                                matched_text=match.group(0),
                                match_source="rule",
                            )

        # Convert to list and sort by confidence
        all_matches = list(matches_map.values())
        all_matches.sort(key=lambda m: m.confidence, reverse=True)

        # Limit tags per type
        final_matches = self._limit_by_type(all_matches)

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        logger.debug(
            f"Rule tagging found {len(final_matches)} tags "
            f"(checked {patterns_checked} patterns in {elapsed_ms:.1f}ms)"
        )

        return RuleTaggingResult(
            matches=final_matches,
            processing_time_ms=elapsed_ms,
            patterns_checked=patterns_checked,
        )

    def _calculate_confidence(
        self,
        match: re.Match,
        pattern_text: str,
        title_lower: str,
        normalized_name: str,
    ) -> float:
        """Calculate confidence score for a match.

        Args:
            match: The regex match object.
            pattern_text: The pattern that matched.
            title_lower: Lowercase title text.
            normalized_name: Normalized tag name.

        Returns:
            Confidence score between 0 and 1.
        """
        # Base confidence
        confidence = 0.7

        # Boost for title match
        if match.group(0).lower() in title_lower:
            confidence += self._config.title_boost

        # Boost for exact match (pattern equals normalized name)
        matched_text = match.group(0).lower()
        if matched_text == normalized_name.lower():
            confidence += self._config.exact_match_boost

        # Cap at 1.0
        return min(confidence, 1.0)

    def _limit_by_type(self, matches: list[TagMatchDTO]) -> list[TagMatchDTO]:
        """Limit matches per tag type.

        Args:
            matches: All matches sorted by confidence.

        Returns:
            Limited list of matches.
        """
        type_counts: dict[TagType, int] = {}
        result: list[TagMatchDTO] = []

        for match in matches:
            count = type_counts.get(match.tag_type, 0)
            if count < self._config.max_tags_per_type:
                result.append(match)
                type_counts[match.tag_type] = count + 1

        return result

    def tag_text(self, text: str) -> RuleTaggingResult:
        """Tag a simple text string.

        Convenience method for tagging plain text.

        Args:
            text: The text to tag.

        Returns:
            RuleTaggingResult with matched tags.
        """
        context = TaggingContext(
            title="",
            excerpt="",
            clean_text=text,
        )
        return self.tag(context)

    def tag_title_and_text(
        self,
        title: str,
        text: str,
    ) -> RuleTaggingResult:
        """Tag title and text.

        Args:
            title: The title text.
            text: The body text.

        Returns:
            RuleTaggingResult with matched tags.
        """
        context = TaggingContext(
            title=title,
            excerpt="",
            clean_text=text,
        )
        return self.tag(context)

    def get_pattern_count(self) -> dict[str, int]:
        """Get count of patterns by type.

        Returns:
            Dictionary mapping tag type to pattern count.
        """
        return {
            tag_type: len(patterns)
            for tag_type, patterns in self._compiled_patterns.items()
        }


# Singleton instance for convenience
_default_tagger: RuleTagger | None = None


def get_rule_tagger() -> RuleTagger:
    """Get the default rule tagger instance.

    Returns:
        The default RuleTagger instance.
    """
    global _default_tagger
    if _default_tagger is None:
        _default_tagger = RuleTagger()
    return _default_tagger
