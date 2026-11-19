# 094 — Conventional Commits

## De afspraak uit de README

> Commitberichten volgen [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, ...).

## Het formaat

```
<type>(<scope>): <korte omschrijving>

<optioneel: langer lichaam>
```

Voorbeelden uit dit project:

```
feat(schema): voeg rotation toe aan Symbol
fix(rules): import van Project corrigeren
docs(doc): sectie ML toegevoegd
test(materials): gevallen voor onbekende typen
chore(ci): promotiegate toegevoegen
```

## De types

| Type | Wanneer |
|---|---|
| `feat` | Nieuwe functionaliteit |
| `fix` | Bugfix |
| `docs` | Alleen documentatie |
| `style` | Formatting, geen logica |
| `refactor` | Herstructureren zonder gedragswijziging |
| `test` | Tests toevoegen of wijzigen |
| `chore` | Onderhoud, dependencies, configuratie |
| `perf` | Prestatieverbetering |
| `build` | Build-systeem |
| `ci` | CI-workflows |

## Waarom het nuttig is

1. **Automatische changelogs.** Met tools als `git-cliff` of `release-please` wordt de changelog uit de commits gegenereerd.
2. **Semver-inschatting.** `feat` versus `fix` zegt iets over de versiestijging.
3. **Zoekbaarheid.** `git log --grep "^fix(rules)"` toont alle regel-wijzigingen — handig bij een regressie.

## De scope's in dit project

Gebruik de mapnaam als scope:

- `schema`, `rules`, `materials`, `parsers`, `vision`, `drawing`
- `api`, `worker`, `mcp`, `web`, `review`
- `ml`, `infra`, `ci`, `doc`

## Breaking changes

```
feat(schema)!: Symbol.circuit wordt een Enum

BREAKING CHANGE: opgeslagen projecten met vrije tekst in circuit
hebben een migratie nodig.
```

Dat is het moment waarop [027-versiebeheer-van-het-schema](027-versiebeheer-van-het-schema.md) in beeld komt.

## Wat er nu bestaat

Er zijn 8 commits in de repo; er is geen commit-hook of linter die het formaat afdwingt. Overweeg `commitlint` in een pre-commit hook, maar begin met cultuur, niet met dwang.
