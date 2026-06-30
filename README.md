# skillreducer

Optimize [Cursor Agent Skills](https://cursor.com/docs) for token efficiency using the **SkillReducer** framework from [arXiv:2603.29919](https://arxiv.org/abs/2603.29919).

Every token in a skill description and body competes for context window space. SkillReducer debloats skills in two stages:

1. **Stage 1 — Routing layer:** compress or generate YAML `description` fields so agents route correctly with fewer tokens.
2. **Stage 2 — Body restructuring:** classify content (core rules, examples, templates, background), keep essentials in `SKILL.md`, and move the rest into on-demand reference files.

## Install

```bash
pip install -e .
```

Optional dev dependencies:

```bash
pip install -e ".[dev]"
```

## Quick start

Audit a skill:

```bash
skillreducer audit path/to/my-skill
```

Reduce a skill (writes to `optimized/` by default):

```bash
skillreducer reduce path/to/my-skill
skillreducer reduce path/to/my-skill --output ./optimized --dry-run
```

Batch mode:

```bash
skillreducer audit ~/.cursor/skills --recursive
skillreducer reduce .cursor/skills --recursive
```

## Configuration

Copy `config.example.yaml` to `config.yaml` or `~/.config/skillreducer/config.yaml`.

Set `OPENAI_API_KEY` (or `SKILLREDUCER_API_KEY`) for LLM-powered segmentation and classification. Without an API key, the tool falls back to heuristics.

```bash
export OPENAI_API_KEY=sk-...
skillreducer reduce path/to/skill
```

Use `--no-llm` to force heuristic-only mode.

## Cursor skill layout

```
my-skill/
├── SKILL.md          # frontmatter + compressed core body
├── examples.md       # on-demand (created by Stage 2)
├── templates.md      # on-demand
├── background.md     # on-demand
└── scripts/          # unchanged (not counted as context bloat)
```

## CLI

| Command | Description |
|---------|-------------|
| `skillreducer audit <path>` | Token report + F1/F2/F3 issue flags |
| `skillreducer reduce <path>` | Run Stage 1 + Stage 2 optimization |
| `--stage 1` / `--stage 2` | Run a single stage |
| `--recursive` | Process all skills under a directory |
| `--dry-run` | Report savings without writing files |
| `--no-llm` | Heuristic mode (no API calls) |

## Safety

- Never modifies skills in-place by default; output goes to `--output`.
- Refuses paths under `skills-cursor` (Cursor built-in skills).

## Development

```bash
pytest
ruff check src tests
```

## Reference

Based on **SkillReducer: Optimizing LLM Agent Skills for Token Efficiency** (Gao et al., 2026). See `skill_reducer.pdf` in this repository.

## License

MIT
