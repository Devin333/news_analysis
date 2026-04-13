"""Classification module for content categorization."""

from app.processing.classification.features import (
    ClassificationFeatures,
    extract_features,
)
from app.processing.classification.board_classifier import (
    BoardClassifier,
    BoardClassificationResult,
    get_board_classifier,
)
from app.processing.classification.content_type_classifier import (
    ContentTypeClassifier,
    ContentTypeResult,
    get_content_type_classifier,
)
from app.processing.classification.service import (
    ClassificationService,
    ClassificationResult,
    get_classification_service,
)

__all__ = [
    "ClassificationFeatures",
    "extract_features",
    "BoardClassifier",
    "BoardClassificationResult",
    "get_board_classifier",
    "ContentTypeClassifier",
    "ContentTypeResult",
    "get_content_type_classifier",
    "ClassificationService",
    "ClassificationResult",
    "get_classification_service",
]
