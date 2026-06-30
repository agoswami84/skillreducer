from __future__ import annotations

import re

from skillreducer.llm.client import LLMClient
from skillreducer.llm import prompts
from skillreducer.models import Skill
from skillreducer.tokenizer import count_tokens


def generate_description(skill: Skill, llm: LLMClient | None) -> str:
    if llm and llm.enabled:
        result = llm.complete_json(prompts.GENERATE_DESCRIPTION.format(body=skill.body[:8000]))
        return str(result.get("description", "")).strip()
    return _heuristic_description(skill)


def _heuristic_description(skill: Skill) -> str:
    title_match = re.search(r"^#\s+(.+)$", skill.body, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else skill.name.replace("-", " ")
    first_para = ""
    for block in re.split(r"\n\s*\n", skill.body):
        block = block.strip()
        if block and not block.startswith("#"):
            first_para = re.sub(r"\s+", " ", block)[:180]
            break
    return (
        f"{title}. {first_para} Use when working with {skill.name.replace('-', ' ')} "
        f"or when the user mentions related tasks."
    ).strip()
