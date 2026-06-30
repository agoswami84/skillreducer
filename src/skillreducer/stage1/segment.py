from __future__ import annotations

import re

from skillreducer.llm.client import LLMClient
from skillreducer.llm import prompts


def segment_description(description: str, llm: LLMClient | None) -> list[str]:
    if llm and llm.enabled:
        result = llm.complete_json(prompts.SEGMENT_DESCRIPTION.format(description=description))
        clauses = result.get("clauses", [])
        return [str(c).strip() for c in clauses if str(c).strip()]
    return _heuristic_segment(description)


def _heuristic_segment(description: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|;\s+|,\s+(?=Use when|Tools:|Triggers:)", description)
    clauses = [p.strip() for p in parts if p.strip()]
    return clauses or [description.strip()]
