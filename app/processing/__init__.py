"""Processing package for content cleaning, normalization, and deduplication."""

from app.processing.cleaner import (
    TextCleaner,
    TitleCleaner,
    clean_text,
    clean_title,
    default_text_cleaner,
    default_title_cleaner,
)
from app.processing.dedup import (
    CompositeDedupStrategy,
    ContentDedupStrategy,
    DedupResult,
    DedupStrategy,
    Deduplicator,
    TitleDedupStrategy,
    URLDedupStrategy,
    default_deduplicator,
    filter_duplicates,
    is_duplicate,
)
from app.processing.normalizer import (
    ContentNormalizer,
    default_normalizer,
    normalize_content,
)
from app.processing.pipeline import (
    PipelineResult,
    ProcessingPipeline,
    default_pipeline,
    process_raw_items,
    process_single_item,
)

__all__ = [
    "CompositeDedupStrategy",
    "ContentDedupStrategy",
    "ContentNormalizer",
    "DedupResult",
    "DedupStrategy",
    "Deduplicator",
    "PipelineResult",
    "ProcessingPipeline",
    "TextCleaner",
    "TitleCleaner",
    "TitleDedupStrategy",
    "URLDedupStrategy",
    "clean_text",
    "clean_title",
    "default_deduplicator",
    "default_normalizer",
    "default_pipeline",
    "default_text_cleaner",
    "default_title_cleaner",
    "filter_duplicates",
    "is_duplicate",
    "normalize_content",
    "process_raw_items",
    "process_single_item",
]
