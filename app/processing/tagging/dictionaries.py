"""Tag dictionaries for rule-based tagging.

This module maintains keyword dictionaries for identifying
companies, frameworks, models, tasks, and domains.
"""

# Company aliases mapping normalized name to display name and aliases
COMPANY_ALIASES: dict[str, dict] = {
    "openai": {
        "name": "OpenAI",
        "aliases": ["open ai", "open-ai"],
    },
    "google": {
        "name": "Google",
        "aliases": ["google ai", "google deepmind", "deepmind"],
    },
    "microsoft": {
        "name": "Microsoft",
        "aliases": ["msft", "ms research", "microsoft research"],
    },
    "meta": {
        "name": "Meta",
        "aliases": ["facebook", "facebook ai", "meta ai", "fair"],
    },
    "anthropic": {
        "name": "Anthropic",
        "aliases": [],
    },
    "amazon": {
        "name": "Amazon",
        "aliases": ["aws", "amazon web services", "amazon ai"],
    },
    "nvidia": {
        "name": "NVIDIA",
        "aliases": ["nvidia ai"],
    },
    "apple": {
        "name": "Apple",
        "aliases": ["apple ai", "apple intelligence"],
    },
    "huggingface": {
        "name": "Hugging Face",
        "aliases": ["hugging face", "hf"],
    },
    "stability": {
        "name": "Stability AI",
        "aliases": ["stability ai", "stable diffusion"],
    },
    "mistral": {
        "name": "Mistral AI",
        "aliases": ["mistral ai"],
    },
    "cohere": {
        "name": "Cohere",
        "aliases": [],
    },
    "baidu": {
        "name": "Baidu",
        "aliases": ["baidu ai", "ernie"],
    },
    "alibaba": {
        "name": "Alibaba",
        "aliases": ["alibaba cloud", "aliyun", "qwen"],
    },
    "tencent": {
        "name": "Tencent",
        "aliases": ["tencent ai"],
    },
    "bytedance": {
        "name": "ByteDance",
        "aliases": ["byte dance", "doubao"],
    },
}

# Framework names
FRAMEWORK_NAMES: dict[str, dict] = {
    "pytorch": {
        "name": "PyTorch",
        "aliases": ["torch"],
    },
    "tensorflow": {
        "name": "TensorFlow",
        "aliases": ["tf", "keras"],
    },
    "jax": {
        "name": "JAX",
        "aliases": ["flax"],
    },
    "langchain": {
        "name": "LangChain",
        "aliases": ["lang chain"],
    },
    "llamaindex": {
        "name": "LlamaIndex",
        "aliases": ["llama index", "llama-index"],
    },
    "transformers": {
        "name": "Transformers",
        "aliases": ["huggingface transformers"],
    },
    "vllm": {
        "name": "vLLM",
        "aliases": [],
    },
    "ollama": {
        "name": "Ollama",
        "aliases": [],
    },
    "mlx": {
        "name": "MLX",
        "aliases": ["apple mlx"],
    },
    "onnx": {
        "name": "ONNX",
        "aliases": ["onnx runtime"],
    },
    "triton": {
        "name": "Triton",
        "aliases": ["triton inference"],
    },
    "ray": {
        "name": "Ray",
        "aliases": ["ray serve", "anyscale"],
    },
    "dspy": {
        "name": "DSPy",
        "aliases": [],
    },
    "autogen": {
        "name": "AutoGen",
        "aliases": ["auto gen"],
    },
    "crewai": {
        "name": "CrewAI",
        "aliases": ["crew ai"],
    },
}

# Model names
MODEL_NAMES: dict[str, dict] = {
    "gpt4": {
        "name": "GPT-4",
        "aliases": ["gpt-4", "gpt 4", "gpt4o", "gpt-4o", "gpt4-turbo"],
    },
    "gpt3": {
        "name": "GPT-3.5",
        "aliases": ["gpt-3.5", "gpt 3.5", "chatgpt", "gpt-3.5-turbo"],
    },
    "claude": {
        "name": "Claude",
        "aliases": ["claude 3", "claude-3", "claude 2", "claude-2", "claude sonnet", "claude opus"],
    },
    "gemini": {
        "name": "Gemini",
        "aliases": ["gemini pro", "gemini ultra", "gemini nano"],
    },
    "llama": {
        "name": "LLaMA",
        "aliases": ["llama 2", "llama-2", "llama 3", "llama-3", "llama2", "llama3"],
    },
    "mistral": {
        "name": "Mistral",
        "aliases": ["mistral 7b", "mixtral", "mistral-7b"],
    },
    "qwen": {
        "name": "Qwen",
        "aliases": ["qwen2", "qwen-2", "qwen 2"],
    },
    "phi": {
        "name": "Phi",
        "aliases": ["phi-2", "phi-3", "phi2", "phi3"],
    },
    "stable_diffusion": {
        "name": "Stable Diffusion",
        "aliases": ["sd", "sdxl", "sd xl", "stable-diffusion"],
    },
    "midjourney": {
        "name": "Midjourney",
        "aliases": ["mid journey", "mj"],
    },
    "dalle": {
        "name": "DALL-E",
        "aliases": ["dall-e", "dall e", "dalle 3", "dall-e 3"],
    },
    "sora": {
        "name": "Sora",
        "aliases": [],
    },
    "whisper": {
        "name": "Whisper",
        "aliases": [],
    },
    "codellama": {
        "name": "Code Llama",
        "aliases": ["code-llama", "codellama"],
    },
    "deepseek": {
        "name": "DeepSeek",
        "aliases": ["deep seek", "deepseek coder"],
    },
}

# Task keywords
TASK_KEYWORDS: dict[str, dict] = {
    "text_generation": {
        "name": "Text Generation",
        "keywords": ["text generation", "language generation", "content generation"],
    },
    "summarization": {
        "name": "Summarization",
        "keywords": ["summarization", "summarize", "summary", "abstractive"],
    },
    "translation": {
        "name": "Translation",
        "keywords": ["translation", "translate", "machine translation", "nmt"],
    },
    "qa": {
        "name": "Question Answering",
        "keywords": ["question answering", "qa", "q&a", "reading comprehension"],
    },
    "classification": {
        "name": "Classification",
        "keywords": ["classification", "categorization", "sentiment analysis"],
    },
    "ner": {
        "name": "Named Entity Recognition",
        "keywords": ["ner", "named entity", "entity recognition", "entity extraction"],
    },
    "code_generation": {
        "name": "Code Generation",
        "keywords": ["code generation", "code completion", "coding assistant"],
    },
    "image_generation": {
        "name": "Image Generation",
        "keywords": ["image generation", "text to image", "text-to-image", "image synthesis"],
    },
    "speech_recognition": {
        "name": "Speech Recognition",
        "keywords": ["speech recognition", "asr", "speech to text", "speech-to-text"],
    },
    "embedding": {
        "name": "Embedding",
        "keywords": ["embedding", "embeddings", "vector representation"],
    },
    "rag": {
        "name": "RAG",
        "keywords": ["rag", "retrieval augmented", "retrieval-augmented"],
    },
    "fine_tuning": {
        "name": "Fine-tuning",
        "keywords": ["fine-tuning", "fine tuning", "finetuning", "lora", "qlora"],
    },
    "agents": {
        "name": "AI Agents",
        "keywords": ["ai agent", "ai agents", "autonomous agent", "agent framework"],
    },
}

# Domain keywords
DOMAIN_KEYWORDS: dict[str, dict] = {
    "nlp": {
        "name": "NLP",
        "keywords": ["nlp", "natural language", "language model", "llm", "large language model"],
    },
    "cv": {
        "name": "Computer Vision",
        "keywords": ["computer vision", "cv", "image recognition", "object detection"],
    },
    "ml": {
        "name": "Machine Learning",
        "keywords": ["machine learning", "ml", "deep learning", "neural network"],
    },
    "robotics": {
        "name": "Robotics",
        "keywords": ["robotics", "robot", "embodied ai"],
    },
    "healthcare": {
        "name": "Healthcare AI",
        "keywords": ["healthcare ai", "medical ai", "biomedical", "drug discovery"],
    },
    "finance": {
        "name": "Finance AI",
        "keywords": ["fintech", "financial ai", "trading ai", "quantitative"],
    },
    "autonomous": {
        "name": "Autonomous Systems",
        "keywords": ["autonomous", "self-driving", "autonomous vehicle"],
    },
    "multimodal": {
        "name": "Multimodal",
        "keywords": ["multimodal", "multi-modal", "vision language", "vlm"],
    },
}


def get_all_patterns() -> dict[str, list[tuple[str, str, str]]]:
    """Get all patterns for matching.

    Returns:
        Dictionary mapping tag_type to list of (pattern, normalized_name, display_name).
    """
    patterns: dict[str, list[tuple[str, str, str]]] = {
        "company": [],
        "framework": [],
        "model": [],
        "task": [],
        "technology_domain": [],
    }

    # Add company patterns
    for normalized, info in COMPANY_ALIASES.items():
        patterns["company"].append((normalized, normalized, info["name"]))
        for alias in info["aliases"]:
            patterns["company"].append((alias.lower(), normalized, info["name"]))

    # Add framework patterns
    for normalized, info in FRAMEWORK_NAMES.items():
        patterns["framework"].append((normalized, normalized, info["name"]))
        for alias in info["aliases"]:
            patterns["framework"].append((alias.lower(), normalized, info["name"]))

    # Add model patterns
    for normalized, info in MODEL_NAMES.items():
        patterns["model"].append((normalized, normalized, info["name"]))
        for alias in info["aliases"]:
            patterns["model"].append((alias.lower(), normalized, info["name"]))

    # Add task patterns
    for normalized, info in TASK_KEYWORDS.items():
        for keyword in info["keywords"]:
            patterns["task"].append((keyword.lower(), normalized, info["name"]))

    # Add domain patterns
    for normalized, info in DOMAIN_KEYWORDS.items():
        for keyword in info["keywords"]:
            patterns["technology_domain"].append((keyword.lower(), normalized, info["name"]))

    return patterns
