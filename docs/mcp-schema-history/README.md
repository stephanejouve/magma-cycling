# MCP Schema History

Snapshots historisés du contrat MCP magma-cycling, un par version taggée.

## Motivation

Chaque release sans snapshot est un point de diff perdu **définitivement** :
on ne peut pas reconstruire le schéma d'une version déjà déployée (backfill
impossible). L'irrattrapabilité justifie une garde dure côté build (BT-058) :
si la génération du snapshot échoue, le build échoue.

Spec Coach AI 2026-08-18 DE-002, D1 (« snapshot dérivé irrattrapable »).

## Contenu d'un snapshot

Structure JSON par tool MCP :

- `name` — nom d'outil (ex: `get-training-statistics`)
- `schema_description` — description exposée au client MCP
- `input_schema` — JSON Schema complet des arguments
- `handler.module` / `handler.function` — coordonnées du handler Python
- `handler.docstring` — docstring Python **introspection ** — capture la
  sémantique déclarée. Un changement de docstring révèle un changement
  de sens même si le schéma reste identique (cas exemplaire
  `intensity_distribution` v3.73→v3.74).

Enveloppe :
- `version` — tag magma-cycling (ex: `v3.74.0`)
- `generated_at` — ISO8601 UTC du build
- `tool_count` — nombre total d'outils
- `tools` — liste triée par nom

## Localisation

- **Release asset** : téléchargeable depuis chaque release GitHub
  `magma-cycling-schemas-v{X.Y.Z}.json`
  ```bash
  gh release download vX.Y.Z --repo stephanejouve/magma-cycling \
    -p 'magma-cycling-schemas-*.json'
  ```
- **Repo (ici)** : ce dossier reste vide par design en V1 — les snapshots
  vivent comme release assets. Ajout futur possible d'un miroir versionné
  post-review de la volumétrie (~200 KB par snapshot × 100+ releases).

## Consommation via MCP

Le tool MCP `get-release-notes(from_version, to_version)` (à venir, ~3h dev
post-D1) agrège :

- **Derived** : diff de schéma + diff des docstrings entre 2 snapshots
- **Declared** : entrées CHANGELOG + PR bodies mergées entre les 2 tags
- **absence_notes** : versions sans entrée déclarée (P3 « absence explicite »
  DE-002)

## Génération manuelle (debug)

```bash
poetry run python -m magma_cycling.scripts.dump_mcp_schemas > snapshot.json
```

Le script `magma_cycling/scripts/dump_mcp_schemas.py` est la source de
vérité. Il fait échouer avec exit 1 si la liste d'outils est vide, garantie
qu'un snapshot attaché à une release n'est jamais un stub silencieux.

## Refs

- BT-058 (issue à ouvrir post-merge du premier snapshot)
- Spec Coach AI DE-002, msg Talk 2026-08-18
- Absorption D3 par docstring introspection (précision Coach AI même message)
