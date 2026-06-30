from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from skillreducer.audit import audit_skill
from skillreducer.config import Config
from skillreducer.llm.client import LLMClient
from skillreducer.models import ReduceReport, TokenStats
from skillreducer.parser import parse_skill_md, write_skill_md
from skillreducer.stage1.compress import compress_description
from skillreducer.stage1.generate import generate_description
from skillreducer.stage2.disclose import (
    deduplicate_existing_references,
    restructure_body,
    write_reference_file,
)
from skillreducer.tokenizer import count_tokens


def reduce_skill(
    path: Path,
    output_dir: Path,
    config: Config | None = None,
    stage: int | None = None,
    dry_run: bool = False,
    llm: Any | None = None,
) -> ReduceReport:
    config = config or Config.load()

    skill = parse_skill_md(path)
    llm_client = llm if llm is not None else LLMClient(config)
    original = audit_skill(path, config)
    notes: list[str] = []

    description = skill.description
    body = skill.body
    new_references: dict[str, str] = {}

    run_stage1 = stage in (None, 1)
    run_stage2 = stage in (None, 2)

    if run_stage1:
        if not description.strip() or count_tokens(description) <= config.short_description_tokens:
            description = generate_description(skill, llm_client if llm_client.enabled else None)
            notes.append("Stage 1: generated description from body")
        if description.strip():
            description, stage1_notes = compress_description(
                description,
                llm_client if llm_client.enabled else None,
                max_restore_steps=config.max_restore_steps,
            )
            notes.extend(stage1_notes)

    if run_stage2 and body.strip():
        body, generated_refs, stage2_notes = restructure_body(
            body,
            llm_client if llm_client.enabled else None,
            min_reference_tokens=config.min_reference_tokens,
        )
        notes.extend(stage2_notes)
        new_references.update(generated_refs)

        existing_refs = deduplicate_existing_references(
            skill.references,
            skill.body,
            config.min_reference_tokens,
        )
        for name, content in existing_refs.items():
            if name not in new_references:
                new_references[name] = content

    out_skill_dir = output_dir / skill.skill_dir.name
    files_written: list[str] = []

    if not dry_run:
        if out_skill_dir.exists():
            shutil.rmtree(out_skill_dir)
        out_skill_dir.mkdir(parents=True, exist_ok=True)

        frontmatter = dict(skill.frontmatter)
        frontmatter["description"] = description
        skill_md_path = out_skill_dir / "SKILL.md"
        write_skill_md(skill_md_path, frontmatter, body)
        files_written.append("SKILL.md")

        scripts_src = skill.skill_dir / "scripts"
        if scripts_src.exists() and scripts_src.is_dir():
            shutil.copytree(scripts_src, out_skill_dir / "scripts")
            files_written.append("scripts/")

        for filename, content in new_references.items():
            ref_path = out_skill_dir / filename
            write_reference_file(ref_path, content, llm_client if llm_client.enabled else None)
            files_written.append(filename)

    optimized_stats = TokenStats(
        description=count_tokens(description),
        body=count_tokens(body),
        references=sum(count_tokens(c) for c in new_references.values()),
    )

    return ReduceReport(
        source=skill.path,
        output=out_skill_dir,
        original_stats=original.stats,
        optimized_stats=optimized_stats,
        description_changed=description != skill.description,
        files_written=files_written,
        stage_notes=notes,
    )
