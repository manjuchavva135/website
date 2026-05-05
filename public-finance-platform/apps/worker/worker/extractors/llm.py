from __future__ import annotations

from worker.extractors.base import ExtractionResult


class LLMExtractor:
    """
    Stub for LLM-based PDF extraction.

    TODO: Implement once the model is chosen (Claude API or local Ollama).
    The implementation should:
      1. Chunk PDF pages into token-safe batches.
      2. Send each batch to the LLM with a structured-output prompt per source_family.
      3. Parse the LLM response into the same record types used by RuleBasedExtractor.
      4. Return an ExtractionResult with parser_name="llm:<model_id>".
    """

    name = "llm"

    def extract(
        self,
        content: bytes,
        document_type: str,
        source_family: str,
        source_url: str = "",
    ) -> ExtractionResult:
        raise NotImplementedError(
            "LLMExtractor is not yet implemented. "
            "Set EXTRACTOR_PROVIDER=rule_based or implement this class."
        )
