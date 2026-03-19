.. _subagent_playbook:

=================
Subagent Playbook
=================

This playbook defines a practical multi-agent workflow for Qlib development.
It is designed around the actual module boundaries in this repository and can
be used for feature work, bug fixes, and refactoring tasks.

Goals
=====

1. Keep parallel changes low-conflict by enforcing strict write ownership.
2. Shorten delivery time by splitting work across independent modules.
3. Preserve quality through role-specific checks and final integration gates.

Recommended Agent Set
=====================

Use two ``explorer`` agents for discovery and seven ``worker`` agents for
implementation.

1. ``repo-arch-explorer``: map module boundaries and critical entry points.
2. ``pipeline-explorer``: map build, test, and CI/release flows.
3. ``data-worker``: data layer and data collectors.
4. ``dataset-feature-worker``: dataset handlers/processors and related tests.
5. ``model-worker``: model training and model contrib modules.
6. ``backtest-worker``: strategy and backtest execution loop.
7. ``workflow-online-worker``: workflow orchestration and online updates.
8. ``rl-worker``: RL modules and RL examples/tests.
9. ``tooling-ci-worker``: Makefile/workflows/developer docs and quality gates.

Ownership Rules
===============

Each worker must only write files in its owned scope.
Cross-boundary edits must be escalated to the integration phase.

1. ``data-worker``
   - ``qlib/data/``
   - ``scripts/data_collector/``
   - ``tests/data_mid_layer_tests/``
2. ``dataset-feature-worker``
   - ``qlib/data/dataset/``
   - ``tests/dataset_tests/``
3. ``model-worker``
   - ``qlib/model/``
   - ``qlib/contrib/model/``
   - ``tests/model/``
4. ``backtest-worker``
   - ``qlib/backtest/``
   - ``qlib/strategy/``
   - ``tests/backtest/``
5. ``workflow-online-worker``
   - ``qlib/workflow/``
   - ``tests/rolling_tests/``
6. ``rl-worker``
   - ``qlib/rl/``
   - ``examples/rl_order_execution/``
   - ``tests/rl/``
7. ``tooling-ci-worker``
   - ``Makefile``
   - ``.github/workflows/``
   - ``docs/developer/``

Execution Protocol
==================

Phase 1: Discover
-----------------

1. Start ``repo-arch-explorer`` and ``pipeline-explorer`` in parallel.
2. Produce a task split with explicit file ownership.
3. Mark blockers that require cross-module agreement.

Phase 2: Implement
------------------

1. Start 2-4 workers in parallel with disjoint write scopes.
2. Require each worker to provide:
   - changed file list
   - behavior change summary
   - commands used for verification
3. Disallow manual refactors outside owned scope.

Phase 3: Integrate
------------------

1. Merge worker outputs and resolve interfaces.
2. Apply any approved cross-boundary changes.
3. Run module-level and repository-level checks.

Phase 4: Verify
---------------

1. Run targeted checks first, then full checks:
   - ``make black``
   - ``make flake8``
   - ``make mypy``
   - ``pytest tests -m "not slow"``
2. For slow-path sensitive changes, run:
   - ``pytest tests -m "slow"``

Prompt Contract
===============

All workers should receive a task prompt with these required constraints.

1. You are not alone in the codebase.
2. Do not revert or overwrite others' edits.
3. Edit only your owned paths.
4. If blocked by out-of-scope files, report a minimal handoff request.
5. Include evidence: changed paths, checks executed, and unresolved risks.

Ready-to-Use Toolkit
====================

Use the helper under ``scripts/subagents/`` to avoid rewriting prompts.

1. ``roles.json`` defines agent catalog, ownership, and checks.
2. ``compose_prompt.py`` generates standardized prompts for explorers/workers.
3. ``README.md`` includes command examples.

Example
=======

.. code-block:: bash

    python scripts/subagents/compose_prompt.py --list
    python scripts/subagents/compose_prompt.py \
      --role model-worker \
      --objective "Add early stopping callback for tree models" \
      --context "Keep recorder artifact compatibility" \
      --acceptance "tests/model pass" \
      --acceptance "No change to qlib/workflow"

