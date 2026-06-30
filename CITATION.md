# Citation

Please cite the **original SkillReducer research paper** when referring to the framework, algorithms, or empirical findings. This repository is a community implementation inspired by that work.

## Paper

**Title:** SkillReducer: Optimizing LLM Agent Skills for Token Efficiency

**Authors:** Yudong Gao, Zongjie Li, Yuanyuan Yuan, Zimo Ji, Pingchuan Ma, Shuai Wang

**Affiliations:** The Hong Kong University of Science and Technology; Tsinghua University; Zhejiang University of Technology

**arXiv:** [2603.29919](https://arxiv.org/abs/2603.29919) (v2, June 2026)

## BibTeX

```bibtex
@article{gao2026skillreducer,
  title   = {SkillReducer: Optimizing LLM Agent Skills for Token Efficiency},
  author  = {Gao, Yudong and Li, Zongjie and Yuan, Yuanyuan and Ji, Zimo and Ma, Pingchuan and Wang, Shuai},
  journal = {arXiv preprint arXiv:2603.29919},
  year    = {2026},
  url     = {https://arxiv.org/abs/2603.29919}
}
```

## APA

Gao, Y., Li, Z., Yuan, Y., Ji, Z., Ma, P., & Wang, S. (2026). *SkillReducer: Optimizing LLM agent skills for token efficiency*. arXiv. https://arxiv.org/abs/2603.29919

## What to attribute

| Use case | Cite |
|----------|------|
| Two-stage debloating pipeline | Gao et al. (2026) |
| DDMIN description compression | Gao et al. (2026) |
| Five-category body taxonomy | Gao et al. (2026) |
| Progressive disclosure restructuring | Gao et al. (2026) |
| Empirical findings (55K skills study) | Gao et al. (2026) |
| This CLI implementation | Optional: this GitHub repository |

## Acknowledgment

The `skillreducer` Python package implements ideas described in Gao et al. (2026). We thank the authors for publishing the framework and empirical study. This project is **not** affiliated with or endorsed by the paper authors unless stated otherwise.

## Key results (from the paper)

For quick reference when discussing expected outcomes:

- **48%** mean description token reduction
- **39%** mean body token reduction
- **86%** functional pass rate on 600 evaluated skills
- **2.8%** average quality improvement (less-is-more effect)
- **0.965** mean retention across five models from four families

See [PAPER_DETAIL.md](PAPER_DETAIL.md) for full methodology and results.
