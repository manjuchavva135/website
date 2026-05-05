from __future__ import annotations

import logging

from worker.extractors.base import ExtractionResult
from worker.extractors.llm import LLMExtractor
from worker.extractors.rule_based import RuleBasedExtractor
from worker.extractors.validators import validate

logger = logging.getLogger(__name__)


class HybridExtractor:
    """
    Runs LLMExtractor first; if validation fails, falls back to RuleBasedExtractor.
    Validation warnings from both passes are merged into the final result.
    """

    name = "hybrid"

    def __init__(self) -> None:
        self._llm = LLMExtractor()
        self._rule = RuleBasedExtractor()

    def extract(
        self,
        content: bytes,
        document_type: str,
        source_family: str,
        source_url: str = "",
    ) -> ExtractionResult:
        try:
            result = self._llm.extract(content, document_type, source_family, source_url)
            failures = validate(result)
            if not failures:
                return result

            logger.warning(
                "LLM extraction failed validation (%d issues); falling back to rule-based. "
                "source_family=%s failures=%s",
                len(failures),
                source_family,
                failures[:5],
            )
            result.warnings.extend([f"[llm-validation-fail] {f}" for f in failures])
            fallback = self._rule.extract(content, document_type, source_family, source_url)
            fallback.warnings = result.warnings + fallback.warnings
            fallback.parser_name = f"hybrid(llm->rule_based)"
            return fallback

        except NotImplementedError:
            # LLMExtractor not yet implemented — silently use rule-based.
            result = self._rule.extract(content, document_type, source_family, source_url)
            result.parser_name = "hybrid(rule_based_only)"
            return result
