"""Dataset loader for evaluation."""

import json
from pathlib import Path
from typing import Any

from app.bootstrap.logging import get_logger
from app.evaluation.schemas import DatasetDTO, DatasetSampleDTO, EvaluationType

logger = get_logger(__name__)

# Default fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures"


class DatasetLoader:
    """Loader for evaluation datasets."""

    def __init__(self, fixtures_dir: Path | None = None) -> None:
        """Initialize the loader.

        Args:
            fixtures_dir: Directory containing fixture files.
        """
        self._fixtures_dir = fixtures_dir or FIXTURES_DIR

    def load_dataset(
        self,
        evaluation_type: EvaluationType,
        version: str = "1.0",
    ) -> DatasetDTO:
        """Load a dataset for an evaluation type.

        Args:
            evaluation_type: Type of evaluation.
            version: Dataset version.

        Returns:
            Loaded dataset.
        """
        filename = f"{evaluation_type.value}_v{version}.json"
        filepath = self._fixtures_dir / filename

        if not filepath.exists():
            logger.warning(f"Dataset file not found: {filepath}")
            return DatasetDTO(
                name=evaluation_type.value,
                evaluation_type=evaluation_type,
                version=version,
                samples=[],
            )

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            samples = [
                DatasetSampleDTO(
                    id=s.get("id", str(i)),
                    input_data=s.get("input", {}),
                    expected_output=s.get("expected", {}),
                    metadata=s.get("metadata", {}),
                    tags=s.get("tags", []),
                )
                for i, s in enumerate(data.get("samples", []))
            ]

            return DatasetDTO(
                name=data.get("name", evaluation_type.value),
                evaluation_type=evaluation_type,
                version=data.get("version", version),
                samples=samples,
                metadata=data.get("metadata", {}),
            )

        except Exception as e:
            logger.error(f"Failed to load dataset {filepath}: {e}")
            return DatasetDTO(
                name=evaluation_type.value,
                evaluation_type=evaluation_type,
                version=version,
                samples=[],
            )

    def load_all_datasets(self) -> dict[EvaluationType, DatasetDTO]:
        """Load all available datasets.

        Returns:
            Dict of evaluation type to dataset.
        """
        datasets = {}
        for eval_type in EvaluationType:
            dataset = self.load_dataset(eval_type)
            if dataset.samples:
                datasets[eval_type] = dataset
        return datasets

    def save_dataset(
        self,
        dataset: DatasetDTO,
    ) -> bool:
        """Save a dataset to file.

        Args:
            dataset: Dataset to save.

        Returns:
            True if saved successfully.
        """
        filename = f"{dataset.evaluation_type.value}_v{dataset.version}.json"
        filepath = self._fixtures_dir / filename

        try:
            self._fixtures_dir.mkdir(parents=True, exist_ok=True)

            data = {
                "name": dataset.name,
                "version": dataset.version,
                "evaluation_type": dataset.evaluation_type.value,
                "metadata": dataset.metadata,
                "samples": [
                    {
                        "id": s.id,
                        "input": s.input_data,
                        "expected": s.expected_output,
                        "metadata": s.metadata,
                        "tags": s.tags,
                    }
                    for s in dataset.samples
                ],
            }

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved dataset to {filepath}")
            return True

        except Exception as e:
            logger.error(f"Failed to save dataset: {e}")
            return False


def create_board_classification_samples() -> list[DatasetSampleDTO]:
    """Create sample data for board classification evaluation."""
    return [
        DatasetSampleDTO(
            id="bc_001",
            input_data={
                "title": "OpenAI releases GPT-5 with improved reasoning",
                "summary": "OpenAI announced GPT-5 today with significant improvements in reasoning capabilities.",
                "source": "techcrunch.com",
            },
            expected_output={"board_type": "tech"},
            tags=["ai", "llm"],
        ),
        DatasetSampleDTO(
            id="bc_002",
            input_data={
                "title": "Federal Reserve raises interest rates by 0.25%",
                "summary": "The Fed announced a quarter-point rate hike amid inflation concerns.",
                "source": "reuters.com",
            },
            expected_output={"board_type": "news"},
            tags=["finance", "economy"],
        ),
        DatasetSampleDTO(
            id="bc_003",
            input_data={
                "title": "New React 19 features announced at React Conf",
                "summary": "React team unveiled new concurrent features and server components improvements.",
                "source": "react.dev",
            },
            expected_output={"board_type": "tech"},
            tags=["frontend", "react"],
        ),
        DatasetSampleDTO(
            id="bc_004",
            input_data={
                "title": "Apple reports record Q4 earnings",
                "summary": "Apple exceeded analyst expectations with strong iPhone and services revenue.",
                "source": "apple.com",
            },
            expected_output={"board_type": "news"},
            tags=["business", "earnings"],
        ),
        DatasetSampleDTO(
            id="bc_005",
            input_data={
                "title": "Kubernetes 1.30 introduces new scheduling features",
                "summary": "The latest Kubernetes release adds improved pod scheduling and resource management.",
                "source": "kubernetes.io",
            },
            expected_output={"board_type": "tech"},
            tags=["devops", "kubernetes"],
        ),
    ]


def create_topic_merge_samples() -> list[DatasetSampleDTO]:
    """Create sample data for topic merge evaluation."""
    return [
        DatasetSampleDTO(
            id="tm_001",
            input_data={
                "topic_a": {
                    "id": 1,
                    "title": "GPT-5 Release Announcement",
                    "items": ["OpenAI announces GPT-5", "GPT-5 features revealed"],
                },
                "topic_b": {
                    "id": 2,
                    "title": "OpenAI GPT-5 Launch",
                    "items": ["GPT-5 launched today", "New GPT model from OpenAI"],
                },
            },
            expected_output={"should_merge": True, "reason": "Same event"},
            tags=["duplicate"],
        ),
        DatasetSampleDTO(
            id="tm_002",
            input_data={
                "topic_a": {
                    "id": 3,
                    "title": "React 19 Release",
                    "items": ["React 19 announced"],
                },
                "topic_b": {
                    "id": 4,
                    "title": "Vue 4 Release",
                    "items": ["Vue 4 released"],
                },
            },
            expected_output={"should_merge": False, "reason": "Different frameworks"},
            tags=["distinct"],
        ),
        DatasetSampleDTO(
            id="tm_003",
            input_data={
                "topic_a": {
                    "id": 5,
                    "title": "AWS re:Invent 2024",
                    "items": ["AWS announces new services at re:Invent"],
                },
                "topic_b": {
                    "id": 6,
                    "title": "Amazon Web Services Conference",
                    "items": ["re:Invent 2024 keynote highlights"],
                },
            },
            expected_output={"should_merge": True, "reason": "Same conference"},
            tags=["duplicate"],
        ),
    ]


def create_historian_quality_samples() -> list[DatasetSampleDTO]:
    """Create sample data for historian quality evaluation."""
    return [
        DatasetSampleDTO(
            id="hq_001",
            input_data={
                "topic_title": "GPT-5 Release",
                "topic_summary": "OpenAI released GPT-5 with improved capabilities",
                "items": [
                    {"title": "GPT-5 announced", "published_at": "2024-01-15"},
                    {"title": "GPT-5 features detailed", "published_at": "2024-01-16"},
                ],
            },
            expected_output={
                "has_historical_context": True,
                "has_timeline": True,
                "mentions_predecessors": True,  # Should mention GPT-4
            },
            tags=["ai", "llm"],
        ),
        DatasetSampleDTO(
            id="hq_002",
            input_data={
                "topic_title": "Kubernetes 1.30 Release",
                "topic_summary": "New Kubernetes version with scheduling improvements",
                "items": [
                    {"title": "K8s 1.30 released", "published_at": "2024-02-01"},
                ],
            },
            expected_output={
                "has_historical_context": True,
                "has_timeline": True,
                "mentions_predecessors": True,  # Should mention previous versions
            },
            tags=["devops"],
        ),
    ]


def create_writer_quality_samples() -> list[DatasetSampleDTO]:
    """Create sample data for writer quality evaluation."""
    return [
        DatasetSampleDTO(
            id="wq_001",
            input_data={
                "topic_title": "New AI Framework Released",
                "source_content": "Company X released a new AI framework today. The framework supports Python and JavaScript. It includes pre-trained models for NLP tasks.",
                "insights": {
                    "importance": 0.7,
                    "key_points": ["New framework", "Multi-language support", "NLP focus"],
                },
            },
            expected_output={
                "min_length": 100,
                "should_mention": ["framework", "Python", "NLP"],
                "tone": "informative",
            },
            tags=["tech"],
        ),
    ]


def initialize_fixtures() -> None:
    """Initialize fixture files with sample data."""
    loader = DatasetLoader()

    # Board classification dataset
    bc_dataset = DatasetDTO(
        name="Board Classification Evaluation",
        evaluation_type=EvaluationType.BOARD_CLASSIFICATION,
        version="1.0",
        samples=create_board_classification_samples(),
        metadata={"description": "Samples for board classification accuracy"},
    )
    loader.save_dataset(bc_dataset)

    # Topic merge dataset
    tm_dataset = DatasetDTO(
        name="Topic Merge Evaluation",
        evaluation_type=EvaluationType.TOPIC_MERGE,
        version="1.0",
        samples=create_topic_merge_samples(),
        metadata={"description": "Samples for topic merge precision/recall"},
    )
    loader.save_dataset(tm_dataset)

    # Historian quality dataset
    hq_dataset = DatasetDTO(
        name="Historian Quality Evaluation",
        evaluation_type=EvaluationType.HISTORIAN_QUALITY,
        version="1.0",
        samples=create_historian_quality_samples(),
        metadata={"description": "Samples for historian agent quality"},
    )
    loader.save_dataset(hq_dataset)

    # Writer quality dataset
    wq_dataset = DatasetDTO(
        name="Writer Quality Evaluation",
        evaluation_type=EvaluationType.WRITER_QUALITY,
        version="1.0",
        samples=create_writer_quality_samples(),
        metadata={"description": "Samples for writer agent quality"},
    )
    loader.save_dataset(wq_dataset)

    logger.info("Initialized evaluation fixtures")


if __name__ == "__main__":
    initialize_fixtures()
