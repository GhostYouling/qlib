# Qlib Subagent Toolkit

This directory contains a practical subagent setup for this repository.

## Files

- `roles.json`: role catalog, ownership scope, and role-specific checks.
- `compose_prompt.py`: generates a standardized prompt for one role/task.

## Why this toolkit exists

Qlib has clear module boundaries (`data`, `model`, `backtest`, `workflow`, `rl`)
and a non-trivial CI pipeline. This setup helps you:

1. split work safely across independent write scopes
2. run roles in parallel with lower merge conflicts
3. enforce consistent output/validation contracts from each agent

## Quick start

List roles:

```bash
python scripts/subagents/compose_prompt.py --list
# or
make subagent-list
```

Generate a worker prompt:

```bash
python scripts/subagents/compose_prompt.py \
  --role model-worker \
  --objective "Add robust early stopping for tree-based models" \
  --context "Keep recorder artifact schema unchanged" \
  --context "Do not edit qlib/workflow" \
  --acceptance "tests/model pass" \
  --acceptance "No behavior change for default trainer path"

# or
make subagent-prompt ROLE=model-worker OBJECTIVE="Add robust early stopping for tree-based models"
```

Generate an explorer prompt:

```bash
python scripts/subagents/compose_prompt.py \
  --role pipeline-explorer \
  --objective "Identify CI gaps in lint/test/release consistency" \
  --acceptance "Provide path-level evidence for each risk"
```

Validate role schema:

```bash
python scripts/subagents/compose_prompt.py --validate
# or
make subagent-validate
```

## Suggested execution order

1. Run `repo-arch-explorer` + `pipeline-explorer` in parallel.
2. Split tasks into disjoint write scopes.
3. Run 2-4 workers in parallel.
4. Integrate and execute repository-level checks.

## Notes

- `compose_prompt.py` only composes prompt text. It does not launch agents.
- Keep role ownership strict to avoid merge and behavior conflicts.
- Role schema is validated by `--validate` and covered by unit tests.
