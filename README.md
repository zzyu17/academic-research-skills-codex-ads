# Academic Research Skills for Codex

Codex-native packaging of the Academic Research Skills suite.

This repository vendors the ARS workflow content as a single Codex skill:

```text
skills/academic-research-suite/
  SKILL.md
  manifest.json
  agents/openai.yaml
  ars/
    deep-research/
    academic-paper/
    academic-paper-reviewer/
    academic-pipeline/
    experiment-agent/
    shared/
```

The original Claude Code ARS checkout is not modified. Upstream content is copied
from fresh GitHub clones and adapted through the Codex router in
`skills/academic-research-suite/SKILL.md`.

## Install

Install the skill from this repo path:

```bash
python /Users/imbad/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo Imbad0202/academic-research-skills-codex \
  --path skills/academic-research-suite
```

Restart Codex after installation.

## Update Policy

Updates are manual cherry-picks from upstream ARS. Do not mirror the Claude Code
repo blindly; review path references and Claude-specific runtime language before
updating this Codex package.

