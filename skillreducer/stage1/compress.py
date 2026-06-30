from __future__ import annotations

import re

from skillreducer.llm.client import LLMClient
from skillreducer.llm import prompts
from skillreducer.stage1.ddmin import ddmin
from skillreducer.stage1.segment import segment_description


def compress_description(
    description: str,
    llm: LLMClient | None,
    max_restore_steps: int = 3,
) -> tuple[str, list[str]]:
    notes: list[str] = []
    original = description.strip()
    if not original:
        return original, notes

    clauses = segment_description(original, llm)
    if len(clauses) <= 1:
        compressed = _polish(clauses, llm)
        return compressed, notes

    def oracle(candidate: list[str]) -> bool:
        return _simulated_oracle_pass(" ".join(candidate), original)

    minimal = ddmin(clauses, oracle)
    deleted = [c for c in clauses if c not in minimal]

    rewritten = [_paraphrase_clause(c, llm) for c in minimal]
    compressed = _polish(rewritten, llm)

    if not _simulated_oracle_pass(compressed, original):
        restored = list(minimal)
        pool = list(deleted)
        for _ in range(max_restore_steps):
            if not pool:
                break
            best = max(pool, key=lambda c: _overlap_score(c, original))
            pool.remove(best)
            restored.append(best)
            trial = _polish(restored, llm)
            if _simulated_oracle_pass(trial, original):
                compressed = trial
                notes.append("Stage 1: selective restore applied")
                break
        else:
            compressed = original
            notes.append("Stage 1: fallback to original description")

    if compressed != original:
        notes.append(f"Stage 1: compressed description ({len(clauses)} -> {len(minimal)} clauses)")
    return compressed, notes


def _paraphrase_clause(clause: str, llm: LLMClient | None) -> str:
    if llm and llm.enabled:
        return llm.complete(prompts.PARAPHRASE_CLAUSE.format(clause=clause)).strip() or clause
    return re.sub(r"\b(use when the user mentions|use when)\b", "Use when", clause, flags=re.I)


def _polish(clauses: list[str], llm: LLMClient | None) -> str:
    text = ". ".join(c.strip().rstrip(".") for c in clauses if c.strip())
    text = re.sub(r"\s+", " ", text).strip()
    if not text.endswith("."):
        text += "."
    return text


def _simulated_oracle_pass(candidate: str, original: str) -> bool:
    cand_tokens = set(re.findall(r"[a-z0-9][a-z0-9_-]{2,}", candidate.lower()))
    orig_tokens = set(re.findall(r"[a-z0-9][a-z0-9_-]{2,}", original.lower()))
    if not cand_tokens:
        return False
    overlap = len(cand_tokens & orig_tokens) / max(len(orig_tokens), 1)
    return overlap >= 0.45 and len(candidate) <= len(original)


def _overlap_score(clause: str, original: str) -> int:
    return len(set(clause.lower().split()) & set(original.lower().split()))
