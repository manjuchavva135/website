from __future__ import annotations

from worker.config import settings
from worker.extractors.base import ExtractorProvider


def get_extractor() -> ExtractorProvider:
    """
    Returns the extractor selected by the EXTRACTOR_PROVIDER env var.
    Defaults to 'rule_based'. Options: rule_based | llm | hybrid.
    """
    provider = getattr(settings, "extractor_provider", "rule_based")

    if provider == "llm":
        from worker.extractors.llm import LLMExtractor
        return LLMExtractor()
    if provider == "hybrid":
        from worker.extractors.hybrid import HybridExtractor
        return HybridExtractor()

    from worker.extractors.rule_based import RuleBasedExtractor
    return RuleBasedExtractor()
