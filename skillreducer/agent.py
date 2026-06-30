"""Agno-based SkillReducer agent — skill folder in, optimized files out."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from skillreducer.agent_prompts import (
    COMPLETION_SYSTEM,
    OPTIMIZE_SKILL_PROMPT,
    SKILL_REDUCER_DESCRIPTION,
    SKILL_REDUCER_INSTRUCTIONS,
)
from skillreducer.audit import audit_skill
from skillreducer.config import Config
from skillreducer.model import create_compression_model, resolve_api_key
from skillreducer.models import ReduceReport
from skillreducer.parser import find_skill_paths, parse_skill_md, resolve_skill_md
from skillreducer.pipeline import reduce_skill
from skillreducer.tokenizer import count_tokens

try:
    from agno.agent import Agent
except ImportError:  # pragma: no cover
    Agent = None  # type: ignore[misc, assignment]


@dataclass
class SkillOptimizationResult:
    """Output of optimizing one skill folder."""

    input_dir: Path
    output_dir: Path
    skill_md: Path
    reference_files: list[Path] = field(default_factory=list)
    scripts_dir: Path | None = None
    report: ReduceReport | None = None
    agent_summary: str = ""

    @property
    def all_files(self) -> list[Path]:
        files = [self.skill_md, *self.reference_files]
        if self.scripts_dir and self.scripts_dir.exists():
            files.append(self.scripts_dir)
        return files


class AgnoLLMClient:
    """Adapter exposing complete/complete_json for pipeline stages via Agno."""

    def __init__(self, agent: Agent) -> None:
        self._agent = agent
        self._enabled = True

    @property
    def enabled(self) -> bool:
        return self._enabled

    def complete(self, prompt: str, model: str | None = None, system: str | None = None) -> str:
        message = prompt
        if system:
            message = f"{system}\n\n{prompt}"
        run = self._agent.run(message)
        content = run.content
        if content is None:
            return ""
        if isinstance(content, str):
            return content.strip()
        return str(content).strip()

    def complete_json(self, prompt: str, model: str | None = None, system: str | None = None) -> Any:
        text = self.complete(prompt, model=model, system=system)
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(text)


def create_completion_agent(config: Config) -> Agent:
    """Lightweight Agno agent for stage-level LLM calls."""
    if Agent is None:
        raise ImportError("agno is not installed. Install with: pip install agno")
    if not resolve_api_key(config):
        raise ValueError("API key required for Agno agent. Set OPENAI_API_KEY or config api_key.")

    return Agent(
        name="skillreducer-llm",
        model=create_compression_model(config),
        description="SkillReducer stage-level LLM helper",
        instructions=[COMPLETION_SYSTEM],
        markdown=False,
        telemetry=False,
    )


def create_skill_reducer_agent(config: Config) -> Agent:
    """Orchestrator Agno agent for skill folder optimization."""
    if Agent is None:
        raise ImportError("agno is not installed. Install with: pip install agno")
    if not resolve_api_key(config):
        raise ValueError("API key required for Agno agent. Set OPENAI_API_KEY or config api_key.")

    return Agent(
        name="skillreducer",
        model=create_compression_model(config),
        description=SKILL_REDUCER_DESCRIPTION,
        instructions=SKILL_REDUCER_INSTRUCTIONS,
        markdown=True,
        telemetry=False,
    )


class SkillReducerAgent:
    """
    Agno-powered SkillReducer.

    Accepts a skill folder (directory containing SKILL.md), runs the two-stage
    pipeline with Agno-backed LLM calls, writes optimized files, and returns paths.
    """

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config.load()
        self._orchestrator = create_skill_reducer_agent(self.config)
        self._llm = AgnoLLMClient(create_completion_agent(self.config))

    @property
    def orchestrator(self) -> Agent:
        return self._orchestrator

    def plan(self, skill_folder: Path) -> str:
        """Run the orchestrator agent with skill context (optional planning step)."""
        skill = parse_skill_md(skill_folder)
        body_preview = skill.body[:4000]
        ref_names = [r.path.name for r in skill.references]
        run = self._orchestrator.run(
            OPTIMIZE_SKILL_PROMPT.format(
                skill_folder=skill_folder,
                skill_name=skill.name,
                desc_tokens=count_tokens(skill.description),
                description=skill.description or "(empty)",
                body_tokens=count_tokens(skill.body),
                body_preview=body_preview,
                reference_list=", ".join(ref_names) if ref_names else "(none)",
            )
        )
        content = run.content
        return content if isinstance(content, str) else str(content or "")

    def optimize(
        self,
        skill_folder: Path,
        output_dir: Path | None = None,
        *,
        stage: int | None = None,
        dry_run: bool = False,
    ) -> SkillOptimizationResult:
        skill_folder = Path(skill_folder).resolve()
        if not resolve_skill_md(skill_folder).exists():
            raise FileNotFoundError(
                f"No SKILL.md found in {skill_folder}. Expected a skill directory as input."
            )

        skill = parse_skill_md(skill_folder)
        out_root = Path(output_dir or Path("optimized")).resolve()
        report = reduce_skill(
            skill_folder,
            output_dir=out_root,
            config=self.config,
            stage=stage,
            dry_run=dry_run,
            llm=self._llm,
        )

        out_skill_dir = report.output
        skill_md = out_skill_dir / "SKILL.md"
        reference_files = sorted(
            p for p in out_skill_dir.iterdir()
            if p.is_file() and p.name.lower() != "skill.md"
        ) if out_skill_dir.exists() else []

        scripts_dir = out_skill_dir / "scripts"
        summary = (
            f"Optimized '{skill.name}': "
            f"{report.original_stats.total} -> {report.optimized_stats.total} tokens "
            f"({report.total_savings * 100:.1f}% savings)."
        )

        return SkillOptimizationResult(
            input_dir=skill_folder,
            output_dir=out_skill_dir,
            skill_md=skill_md,
            reference_files=reference_files,
            scripts_dir=scripts_dir if scripts_dir.exists() else None,
            report=report,
            agent_summary=summary,
        )

    def optimize_many(
        self,
        root: Path,
        output_dir: Path | None = None,
        *,
        recursive: bool = False,
        stage: int | None = None,
        dry_run: bool = False,
    ) -> list[SkillOptimizationResult]:
        results: list[SkillOptimizationResult] = []
        for skill_path in find_skill_paths(Path(root), recursive=recursive):
            results.append(
                self.optimize(skill_path, output_dir=output_dir, stage=stage, dry_run=dry_run)
            )
        return results
