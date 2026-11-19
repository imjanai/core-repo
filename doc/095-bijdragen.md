# 095 — Werken aan het project

## De stappen uit de README

1. Maak een branch: `git checkout -b feature/mijn-feature`
2. Schrijf tests en houd `ruff` en `mypy` schoon
3. Controleer dat de evaluatieset niet verslechtert (bij ML-wijzigingen)
4. Open een pull request met een duidelijke beschrijving

## Voor je begint

- Lees [006-ontwerpprincipes](006-ontwerpprincipes.md) — de zes uitgangspunten bepalen of een voorstel past.
- Kijk in [030-schema-verschillen-met-readme](030-schema-verschillen-met-readme.md) wat er al openstaat.
- Bij twijfel over richting: [099-open-vragen](099-open-vragen.md).

## De lokale cyclus

```bash
uv run ruff check .
uv run ruff format .
uv run mypy .
uv run pytest
```

Alles groen vóór je pusht. Zie [082-lint-types-format](082-lint-types-format.md) en [081-teststrategie](081-teststrategie.md).

## Regels die dit project specifiek maken

### 1. Het schema is heilig

Wijzigingen in `packages/schema` raken alles. Doe ze:

- additief, met defaults,
- met een round-trip-test,
- met een notitie in de PR.

Zie [027-versiebeheer-van-het-schema](027-versiebeheer-van-het-schema.md) en [029-schema-uitbreiden](029-schema-uitbreiden.md).

### 2. Geen modelaannames in rekencode

Een nieuwe regel of materiaalberekening bevat geen taalmodel. Zie [006-principe 3](006-ontwerpprincipes.md).

### 3. ML-wijzigingen vragen een evaluatie

Een PR die de detector of het VLM raakt, bevat het evaluatierapport. Zie [069-metrics](069-metrics.md) en [083-cicd](083-cicd.md).

### 4. Privacy

Geen klanttekeningen, geen screenshots met adresgegevens, geen datasets in de PR. Zie [084-veiligheid-en-avg](084-veiligheid-en-avg.md).

## De PR-beschrijving

```markdown
## Wat
Kort wat er veranderd.

## Waarom
Het probleem dat het oplost.

## Hoe getest
- [ ] unit-tests toegevoegd
- [ ] ruff + mypy schoon
- [ ] evaluatieset (bij ML): rapport in bijlage

## Risico's
Wat er mis kan gaan; rollback-plan.
```

## Commitstijl

Conventional Commits: [094-conventional-commits](094-conventional-commits.md).
