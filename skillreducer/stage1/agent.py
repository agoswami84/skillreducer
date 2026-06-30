"""Stage 1 Agno routing agent."""

from __future__ import annotations

from dataclasses import dataclass, field

from skillreducer.config import Config
from skillreducer.llm.agno_client import AgnoLLMClient
from skillreducer.model import create_routing_model, resolve_api_key
from skillreducer.models import Skill
from skillreducer.stage1.compress import compress_description
from skillreducer.stage1.generate import generate_description
from skillreducer.stage1.prompts import (
    GENERATE_FROM_BODY_PROMPT,
    ROUTING_ORACLE_PROMPT,
    STAGE1_DESCRIPTION,
    STAGE1_INSTRUCTIONS,
)
from skillreducer.tokenizer import count_tokens

try:
    from agno.agent import Agent
except ImportError:  # pragma: no cover
    Agent = None  # type: ignore[misc, assignment]


@dataclass
class Stage1Result:
    description: str
    notes: list[str] = field(default_factory=list)
    generated: bool = False
    compressed: bool = False


def create_stage1_routing_agent(config: Config) -> Agent:
    """Agno agent dedicated to Stage 1 routing-layer optimization."""
    if Agent is None:
        raise ImportError("agno is not installed. Install with: pip install agno")
    if not resolve_api_key(config):
        raise ValueError("API key required. Set OPENAI_API_KEY or config api_key.")

    return Agent(
        name="skillreducer-stage1-routing",
        model=create_routing_model(config),
        description=STAGE1_DESCRIPTION,
        instructions=STAGE1_INSTRUCTIONS,
        markdown=False,
        telemetry=False,
    )


class Stage1RoutingAgent:
    """
    Stage 1 pipeline backed by a dedicated Agno routing agent.

    Flow (per Gao et al. 2026, Section IV-A):
      1. Generate description if missing or <= threshold tokens
      2. Segment description into semantic clauses
      3. DDMIN — find 1-minimal clause subset (simulated routing oracle)
      4. Paraphrase each retained clause shorter
      5. Selective restore if oracle fails (up to max_restore_steps)
    """

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config.load()
        self._agent = create_stage1_routing_agent(self.config)
        self._llm = AgnoLLMClient(self._agent)

    @property
    def agent(self) -> Agent:
        return self._agent

    @property
    def llm(self) -> AgnoLLMClient:
        return self._llm

    def generate(self, skill: Skill) -> str:
        """Generate a routing description from skill body via Agno agent."""
        result = self._llm.complete_json(
            GENERATE_FROM_BODY_PROMPT.format(
                skill_name=skill.name,
                body=skill.body[:8000],
            )
        )
        if isinstance(result, dict) and result.get("description"):
            return str(result["description"]).strip()
        return generate_description(skill, self._llm)

    def routing_oracle(self, skill_name: str, candidate: str, queries: list[str]) -> bool:
        """Ask the routing agent whether a description passes the simulated oracle."""
        if not queries:
            return True
        query_block = "\n".join(f"- {q}" for q in queries)
        result = self._llm.complete_json(
            ROUTING_ORACLE_PROMPT.format(
                skill_name=skill_name,
                candidate_description=candidate,
                queries=query_block,
            )
        )
        if isinstance(result, dict):
            return bool(result.get("passes", False))
        return False

    def _default_queries(self, skill: Skill) -> list[str]:
        """Routing test queries derived from skill name and body headings."""
        queries = [
            f"Help me with {skill.name.replace('-', ' ')}",
            f"I need to use the {skill.name} skill",
        ]
        for line in skill.body.splitlines():
            if line.startswith("# ") and len(queries) < self.config.num_test_queries:
                queries.append(f"User asks about: {line.lstrip('# ').strip()}")
        return queries[: self.config.num_test_queries]

    def compress(self, description: str, skill: Skill | None = None) -> tuple[str, list[str]]:
        """Compress description using DDMIN + Agno paraphrase; optional agent oracle."""
        compressed, notes = compress_description(
            description,
            self._llm,
            max_restore_steps=self.config.max_restore_steps,
        )
        if skill and compressed != description:
            queries = self._default_queries(skill)
            if not self.routing_oracle(skill.name, compressed, queries):
                notes.append("Stage 1: Agno routing oracle failed after compression; keeping DDMIN result")
        return compressed, notes

    def run(self, skill: Skill) -> Stage1Result:
        """Execute full Stage 1 on a parsed skill. Returns optimized description."""
        notes: list[str] = []
        description = skill.description.strip()
        generated = False
        compressed = False

        if not description or count_tokens(description) <= self.config.short_description_tokens:
            description = self.generate(skill)
            generated = True
            notes.append("Stage 1: Agno agent generated description from body")

        if description:
            new_desc, compress_notes = self.compress(description, skill=skill)
            notes.extend(compress_notes)
            if new_desc != description:
                compressed = True
            description = new_desc

        return Stage1Result(
            description=description,
            notes=notes,
            generated=generated,
            compressed=compressed,
        )
