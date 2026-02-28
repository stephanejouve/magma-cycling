# Memory Graph Experiments

**Date:** 8 février 2026
**Author:** Stéphane Jouve
**Status:** Archived (experimentation completed)

---

## Purpose

Expérimentation avec le package Python `memory_graph` pour visualiser les références mémoire et patterns d'aliasing dans les structures de données du projet magma-cycling.

## Files

### Test Scripts
- `test_memory_graph.py` - Test sur données réelles S079 (week_planning)
- `test_memory_graph_simple.py` - 3 exemples pédagogiques:
  - Exemple 1: Aliasing de listes
  - Exemple 2: Structures imbriquées partagées
  - Exemple 3: Tracking de sessions avec références

### Visualizations (Graphviz)
- `memory_graph_planning.gv` - Planning S079 complet
- `memory_graph_sessions.gv` - Sessions par statut
- `example1_aliasing.gv` - Démo aliasing
- `example2_nested.gv` - Démo nested structures
- `example3_session_tracking.gv` - Démo session tracking

### Tooling
- `generate_visualizations.sh` - Script conversion .gv → PDF (requiert Graphviz)

## Usage

```bash
# View .gv files online
# Upload to: https://dreampuf.github.io/GraphvizOnline/

# Or generate PDFs locally (requires Graphviz)
brew install graphviz
./generate_visualizations.sh
open *.pdf
```

## Dependencies

```bash
# Added to pyproject.toml (8 Feb 2026)
poetry add memory_graph
```

## Outcome

✅ Successfully demonstrated memory visualization for Python data structures
❌ Not integrated into production codebase (experimental only)

## Reason for Archiving

- Expérimentation réussie mais non nécessaire pour le projet
- Fichiers polluaient la racine du projet
- Conservés pour référence future si besoin de débugger aliasing issues
