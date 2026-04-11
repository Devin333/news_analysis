"""Parsers package for extracting structured content from raw items."""

from app.parsers.base import BaseParser
from app.parsers.html import HTMLParser
from app.parsers.json_parser import JSONParser
from app.parsers.manager import ParseJobResult, ParserManager
from app.parsers.registry import ParserRegistry, get_parser_registry, register_parser
from app.parsers.rss import RSSParser

__all__ = [
    "BaseParser",
    "HTMLParser",
    "JSONParser",
    "ParseJobResult",
    "ParserManager",
    "ParserRegistry",
    "RSSParser",
    "get_parser_registry",
    "register_parser",
]
