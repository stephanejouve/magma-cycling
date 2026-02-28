# GitHub Actions CI/CD

## Workflows

### ci-mcp.yml - MCP Tools CI/CD Pipeline

Pipeline complet de validation pour les outils MCP:

**Jobs:**

1. **lint** - Code Quality
   - Black (formatting)
   - Ruff (linting)
   - isort (import sorting)

2. **test** - Tests (Python 3.11, 3.12, 3.13)
   - pytest avec coverage
   - Tests de régression MCP
   - Upload coverage vers Codecov

3. **mcp-validation** - Validation MCP Schemas
   - Vérification des schémas JSON
   - Validation des outils critiques
   - Test du fix additionalProperties

4. **status** - Status Check
   - Agrégation des résultats
   - Bloque le merge si échec

**Déclenchement:**
- Push sur `main` ou `develop`
- Pull Requests vers `main` ou `develop`

**Protection des branches:**
- Tous les jobs doivent passer pour merge
- Tests obligatoires: lint + test + mcp-validation

## Tests Couverts

- ✅ `test_mcp_edge_cases.py` - 7 tests de régression
- ✅ `test_mcp_tools_comprehensive.py` - 17 tests approfondis

### Tests Critiques

**daily-sync:**
- Retourne `{}` au lieu de `None`
- Gère les listes avec `None`
- Protège contre `activity_dates` vide

**analyze-session-adherence:**
- Utilise `tss_planned` (pas `planned_tss`)
- Utilise `duration_min` (pas `planned_duration`)

**update-athlete-profile:**
- Schema avec `additionalProperties: true`
- Accepte des champs dynamiques

## Ajouter un Badge

Ajoutez ce badge dans votre README:

```markdown
![CI Status](https://github.com/stephanejouve/magma-cycling/workflows/CI%2FCD%20Pipeline/badge.svg)
```

## Configuration Locale

Pour lancer la CI localement avant de push:

```bash
# Linting
poetry run black --check .
poetry run ruff check .
poetry run isort --check-only .

# Tests
poetry run pytest tests/test_mcp_edge_cases.py -v

# Validation MCP
poetry run python -c "
import asyncio
from magma_cycling.mcp_server import list_tools
asyncio.run(list_tools())
"
```

## Débogage

Si la CI échoue:

1. **Lint errors**: Lancez `poetry run black .` et `poetry run ruff check --fix .`
2. **Test failures**: Vérifiez les logs dans l'onglet Actions
3. **Schema errors**: Vérifiez que `additionalProperties: true` est présent

## Performance

- Cache des dépendances Poetry (~2-3min → ~30s)
- Matrix strategy pour tester 3 versions Python en parallèle
- Tests rapides uniquement (edge cases)
