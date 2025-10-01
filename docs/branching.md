# Branching Guide

This module lives on top of FastAPI and stays intentionally small, so we are keeping
the branching rules short and explicit. The diagram below is what we expect to show
during the P02 defence.

```
main ──┐
      ├─ p02/feature-<task>  (work branch per issue)
      └─ release/p02         (optional staging branch for demos)
```

- `main` contains only reviewed code. Direct pushes are disabled.
- Every homework task starts from the latest `main` and goes into a branch named
  `p02/<short-task-slug>`, for example `p02/ideas-crud`.
- When several related branches are merged we can cut `release/p02` and tag the
  state with `P02` before presenting the feature.

If you create a new branch, please:

1. Run `git checkout main && git pull` to have the latest base.
2. Start work with `git checkout -b p02/<short-task-slug>`.
3. Reference the issue id in the branch description (`git branch --edit-description`).
4. Open the pull request into `main` only after the automated checks are green.

This note, together with the pull request template, is enough evidence for the
branching model that the checklist asks for.
