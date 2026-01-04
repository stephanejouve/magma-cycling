#!/usr/bin/env python3
"""
Fix D401 docstring errors - convert French infinitives to English imperatives.

Converts docstring first lines from French infinitive form to English imperative mood.
Examples:
    - "Initialiser le client" → "Initialize the client"
    - "Calculer le total" → "Calculate the total"
    - "Valider les données" → "Validate the data"

Usage:
    python scripts/fix_d401_docstrings.py
"""
import re
from pathlib import Path

# Mapping of French infinitives to English imperatives
VERB_MAPPING = {
    # Core verbs (most common)
    "Initialiser": "Initialize",
    "Calculer": "Calculate",
    "Collecter": "Collect",
    "Valider": "Validate",
    "Formater": "Format",
    "Uploader": "Upload",
    "Retourner": "Return",
    "Vérifier": "Verify",
    "Générer": "Generate",
    "Créer": "Create",
    "Récupérer": "Retrieve",
    "Obtenir": "Get",
    "Afficher": "Display",
    "Charger": "Load",
    "Sauvegarder": "Save",
    "Envoyer": "Send",
    "Télécharger": "Download",
    "Importer": "Import",
    "Exporter": "Export",
    "Analyser": "Analyze",
    "Traiter": "Process",
    "Convertir": "Convert",
    "Transformer": "Transform",
    "Mettre à jour": "Update",
    "Ajouter": "Add",
    "Supprimer": "Delete",
    "Modifier": "Modify",
    "Remplacer": "Replace",
    "Rechercher": "Search",
    "Trouver": "Find",
    "Filtrer": "Filter",
    "Trier": "Sort",
    "Comparer": "Compare",
    "Copier": "Copy",
    "Déplacer": "Move",
    "Exécuter": "Execute",
    "Lancer": "Launch",
    "Démarrer": "Start",
    "Arrêter": "Stop",
    "Fermer": "Close",
    "Ouvrir": "Open",
    "Lire": "Read",
    "Écrire": "Write",
    "Appeler": "Call",
    "Invoquer": "Invoke",
    "Construire": "Build",
    "Détruire": "Destroy",
    "Nettoyer": "Clean",
    "Réinitialiser": "Reset",
    "Restaurer": "Restore",
    "Synchroniser": "Synchronize",
    "Connecter": "Connect",
    "Déconnecter": "Disconnect",
    "Enregistrer": "Register",
    "Désinscrire": "Unregister",
    "Activer": "Activate",
    "Désactiver": "Deactivate",
    "Autoriser": "Authorize",
    "Authentifier": "Authenticate",
    "Parser": "Parse",
    "Encoder": "Encode",
    "Décoder": "Decode",
    "Compresser": "Compress",
    "Décompresser": "Decompress",
    "Chiffrer": "Encrypt",
    "Déchiffrer": "Decrypt",
    "Hasher": "Hash",
    "Serialiser": "Serialize",
    "Deserialiser": "Deserialize",
}


def fix_docstring_imperative(content: str) -> tuple[str, int]:
    """
    Fix French infinitive verbs in docstrings to English imperative mood.

    Args:
        content: File content as string

    Returns:
        Tuple of (fixed_content, number_of_fixes)
    """
    lines = content.split("\n")

    fixes = 0
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Check if this is a docstring start
        if stripped.startswith('"""') or stripped.startswith("'''"):
            quote_type = '"""' if '"""' in stripped else "'''"

            # Single-line docstring
            if stripped.count(quote_type) >= 2:
                # Extract text between quotes
                start_idx = stripped.find(quote_type) + 3
                end_idx = stripped.rfind(quote_type)
                if start_idx < end_idx:
                    docstring_text = stripped[start_idx:end_idx]
                    # Check and fix first word
                    fixed_text = fix_first_word(docstring_text)
                    if fixed_text != docstring_text:
                        indent = line[: len(line) - len(line.lstrip())]
                        lines[i] = f"{indent}{quote_type}{fixed_text}{quote_type}"
                        fixes += 1

            # Multi-line docstring
            elif stripped.count(quote_type) == 1:
                # Check if first line has text after opening quotes
                if len(stripped) > 3:
                    text_after_quotes = stripped[3:]
                    fixed_text = fix_first_word(text_after_quotes)
                    if fixed_text != text_after_quotes:
                        indent = line[: len(line) - len(line.lstrip())]
                        lines[i] = f"{indent}{quote_type}{fixed_text}"
                        fixes += 1
                # Otherwise, the actual text is on the next line
                elif i + 1 < len(lines):
                    next_line = lines[i + 1]
                    next_stripped = next_line.strip()
                    if next_stripped and not next_stripped.startswith(quote_type):
                        fixed_text = fix_first_word(next_stripped)
                        if fixed_text != next_stripped:
                            indent = next_line[: len(next_line) - len(next_line.lstrip())]
                            lines[i + 1] = f"{indent}{fixed_text}"
                            fixes += 1

        i += 1

    return "\n".join(lines), fixes


def fix_first_word(text: str) -> str:
    """
    Fix the first word of a docstring if it's a French infinitive.

    Args:
        text: Docstring text

    Returns:
        Fixed text with English imperative
    """
    # Try each French verb pattern

    for french, english in VERB_MAPPING.items():
        # Match the French verb at the start of the string (case-insensitive)
        pattern = re.compile(rf"^{re.escape(french)}\b", re.IGNORECASE)
        if pattern.match(text):
            # Replace while preserving the rest of the text
            fixed = pattern.sub(english, text, count=1)
            return fixed

    return text


def main():
    """Command-line entry point for fixing D401 docstring errors."""
    # Find all Python files

    python_files = []
    for directory in ["cyclisme_training_logs", "tests", "scripts"]:
        path = Path(directory)
        if path.exists():
            python_files.extend(path.rglob("*.py"))

    total_fixes = 0
    files_modified = 0

    print("=" * 70)
    print("FIX D401 - IMPERATIVE MOOD")
    print("=" * 70)
    print()

    for file_path in sorted(python_files):
        content = file_path.read_text(encoding="utf-8")
        fixed_content, fixes = fix_docstring_imperative(content)

        if fixes > 0:
            file_path.write_text(fixed_content, encoding="utf-8")
            total_fixes += fixes
            files_modified += 1
            print(f"✓ {file_path}: {fixes} fix(es)")

    print()
    print("=" * 70)
    print(f"TOTAL: {total_fixes} fixes in {files_modified} files")
    print("=" * 70)


if __name__ == "__main__":
    main()
