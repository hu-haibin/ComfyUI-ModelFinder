# Refactor Guardrails

This document is the single source of truth for the current `ComfyUI-ModelFinder` refactor.

## Scope

- Only the Python repository `ComfyUI-ModelFinder` is in scope.
- `ComfyLauncher_Project` is explicitly out of scope.
- The current baseline is a backend-focused refactor with no intended user-visible change.

## Approved UX Scope Change

- The current UX phase explicitly allows consolidating the former `单个处理` and `批量处理` tabs into one `工作流` tab.
- This scope change is limited to entry consolidation and reduced switching overhead.
- The underlying single-file and batch processing chains remain unchanged.
- CSV / HTML / batch summary output contracts remain unchanged.

## Frozen User Boundary

The following items are frozen during this refactor:

- Main window layout does not change.
- Existing button entry points do not change.
- Main user workflows do not change.
- Output formats do not change.

## Allowed Internal Changes

The following changes are allowed:

- Internal class splitting.
- Service extraction.
- Duplicate code removal.
- Import cleanup.
- Naming cleanup.
- File ownership cleanup.
- Test additions and refactor-safety coverage.

## Explicit Non-Goals

The following are not goals of this refactor:

- No new features.
- No UI redesign.
- No CLI mode.
- No microservice split.
- No complex dependency injection framework.
- No full rewrite.
- No empty abstractions created only for architecture aesthetics.

## Service Rules

- Services must accept explicit inputs and must not read UI state directly.
- Services must not show dialogs or mutate UI widgets.
- Expected failures should return structured failure results instead of raising UI-facing exceptions where practical.
- `analysis_model.py` is now a compatibility facade only. New business logic should move into focused services.

## Legacy UI Handling

- Half-connected `model_mover` and `model_registry` UI code is not part of the active user flow.
- During this refactor, those paths must be hidden and isolated from the main view instead of being completed as new functionality.
- Git history remains the source of truth for removed legacy implementations.

## Boundary Proof Checklist

Every refactor-oriented commit should be able to prove all of the following:

- `pytest -q` passes.
- No new user-visible entry point was added.
- No existing button label or workflow step was changed intentionally.
- No main notebook tab was added, removed, or reordered without an explicit scope change.
- CSV column order is unchanged.
- HTML report still exposes the same core fields and links.
- Batch summary output file name and columns are unchanged.
- Changes are internal restructuring only.

## Phase Anchors

The current planned sequence is:

1. Freeze the boundary and add guardrails.
2. Thin `controller.py` into a UI orchestration layer.
3. Isolate legacy `view.py` residue.
4. Continue retiring `AnalysisModel` into focused backend services.
5. Unify service interface style.
6. Extract adapters and repositories around unstable external dependencies.
7. Strengthen controller and output contract tests.
8. Reorganize directories only after responsibilities are stable.
