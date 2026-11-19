# 083 — CI/CD met GitHub Actions

## De belofte uit de README

> CI (GitHub Actions) draait lint, types en tests bij elke pull request. Wijzigingen aan modellen of de pipeline moeten de evaluatieset passeren zonder regressie.

## De workflow (voorstel)

```yaml
# .github/workflows/ci.yml
name: CI
on: [pull_request]

jobs:
  code:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync
      - run: uv run ruff check .
      - run: uv run ruff format --check .
      - run: uv run mypy .
      - run: uv run pytest
```

## De promotiegate voor modellen

Aparte workflow, want die draait op een GPU-runner en is duur:

```yaml
# .github/workflows/model-eval.yml
name: Model evaluatie
on:
  workflow_dispatch:
    inputs:
      model_pad: {required: true}

jobs:
  eval:
    runs-on: [self-hosted, gpu]
    steps:
      - uses: actions/checkout@v4
      - run: uv sync
      - run: uv run dvc pull ml/data/golden
      - run: uv run python ml/eval/run_eval.py --model ${{ inputs.model_pad }} --baseline production
```

Dat commando staat al in de README:

```bash
uv run python ml/eval/run_eval.py --model elektro-vl
```

## Wat de gate beslist

```
geen regressie op enige metric?
   ├─ ja  → promotie toestaan
   └─ nee → afwijzen, rapport als artefact
```

De metrics: [069-metrics](069-metrics.md). De set: [068-evaluatieset](068-evaluatieset.md).

## Wat er nog bij komt

| Stap | Wanneer |
|---|---|
| Docker-build en push | Vanaf Fase 1 |
| DB-migratie uitvoeren bij deploy | Vanaf Fase 1 |
| Security-scan (dependencies, containers) | Vanaf Fase 1 |
| E2E-test tegen een draaiende stack | Vanaf Fase 1 |
| Deploy naar productie | Pas na review |

## Waar de gate mis kan gaan

| Risico | Gevolg | Mitigatie |
|---|---|---|
| GPU-runner ontbreekt | Model never promoted | Eigen runner of handmatige release |
| Evaluatieset lekt in de workflow | Valse zekerheid | `golden/` alleen via DVC, aparte sleutel |
| Gate wordt omzeild bij spoed | Regressie in productie | Branch protection: gate is verplicht |
| Metrics worden bijgesteld na tune | Selectie-bias | Metrics vastleggen in een version-config |

## Branch protection

- minstens één review,
- CI groen (inclusief promotiegate voor ML-wijzigingen),
- geen force-push op `master`.

Zie ook [081-teststrategie](081-teststrategie.md) en [094-conventional-commits](094-conventional-commits.md).

## Wat er nu bestaat

Niets. Er is geen `.github/`-map.
