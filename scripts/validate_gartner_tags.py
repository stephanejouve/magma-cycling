#!/usr/bin/env python3
"""
Script de validation des tags Gartner TIME dans les docstrings.

GARTNER_TIME: I
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P2
DOCSTRING: v2

Valide que tous les fichiers Python du projet ont des docstrings conformes
au standard v2 avec tags Gartner TIME (I/T/M/E).

Examples:
    Validation complète du projet::

        poetry run python scripts/validate_gartner_tags.py

    Validation d'un fichier spécifique::

        poetry run python scripts/validate_gartner_tags.py --file workflow_coach.py

    Génération rapport HTML::

        poetry run python scripts/validate_gartner_tags.py --html report.html

Author: Claude Code
Created: 2025-12-26
"""
import argparse
import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ValidationResult:
    """Résultat de validation d'un fichier."""

    file_path: Path
    valid: bool
    errors: list[str]
    warnings: list[str]
    gartner_tag: str = ""
    status: str = ""
    priority: str = ""
    docstring_version: str = ""


class GartnerTagValidator:
    """Validateur de tags Gartner TIME dans les docstrings."""

    REQUIRED_TAGS = ["GARTNER_TIME", "STATUS", "LAST_REVIEW", "PRIORITY", "DOCSTRING"]
    VALID_GARTNER_VALUES = ["I", "T", "M", "E"]
    VALID_PRIORITIES = ["P0", "P1", "P2", "P3", "P4"]

    def __init__(self, project_root: Path):
        """
        Initialize le validateur.

        Args:
            project_root: Racine du projet Python à valider
        """
        self.project_root = project_root

    def validate_file(self, file_path: Path) -> ValidationResult:
        """
        Validate un fichier Python.

        Args:
            file_path: Chemin du fichier à valider

        Returns:
            ValidationResult avec détails de validation
        """
        errors = []
        warnings = []

        # Lire le fichier
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return ValidationResult(
                file_path=file_path,
                valid=False,
                errors=[f"Impossible de lire le fichier: {e}"],
                warnings=[],
            )

        # Parser AST
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            return ValidationResult(
                file_path=file_path,
                valid=False,
                errors=[f"Erreur syntaxe Python: {e}"],
                warnings=[],
            )

        # Extraire docstring
        docstring = ast.get_docstring(tree)

        if not docstring:
            return ValidationResult(
                file_path=file_path, valid=False, errors=["Missing module docstring"], warnings=[]
            )

        # Vérifier tags requis
        result = ValidationResult(file_path=file_path, valid=True, errors=[], warnings=[])

        for tag in self.REQUIRED_TAGS:
            if f"{tag}:" not in docstring:
                errors.append(f"Missing required tag: {tag}")

        # Extraire et valider GARTNER_TIME
        gartner_match = re.search(r"GARTNER_TIME:\s*([ITME])", docstring)
        if gartner_match:
            result.gartner_tag = gartner_match.group(1)
            if result.gartner_tag not in self.VALID_GARTNER_VALUES:
                errors.append(f"Invalid GARTNER_TIME value: {result.gartner_tag}")
        else:
            if "GARTNER_TIME:" in docstring:
                errors.append("GARTNER_TIME tag present but invalid format")

        # Extraire STATUS
        status_match = re.search(r"STATUS:\s*(.+)", docstring)
        if status_match:
            result.status = status_match.group(1).strip()

        # Extraire PRIORITY
        priority_match = re.search(r"PRIORITY:\s*(P[0-4])", docstring)
        if priority_match:
            result.priority = priority_match.group(1)
            if result.priority not in self.VALID_PRIORITIES:
                errors.append(f"Invalid PRIORITY value: {result.priority}")

        # Extraire DOCSTRING version
        docstring_match = re.search(r"DOCSTRING:\s*(.+)", docstring)
        if docstring_match:
            result.docstring_version = docstring_match.group(1).strip()

        # Vérifier LAST_REVIEW format
        review_match = re.search(r"LAST_REVIEW:\s*(\d{4}-\d{2}-\d{2})", docstring)
        if not review_match and "LAST_REVIEW:" in docstring:
            errors.append("LAST_REVIEW format incorrect (attendu: YYYY-MM-DD)")

        # Vérifier Examples section
        if "Examples:" not in docstring:
            warnings.append("Missing Examples section")
        else:
            # Compter les code blocks (::)
            code_blocks = docstring.count("::")
            if code_blocks < 2:
                warnings.append("Examples section should have at least 2 code blocks")

        # Vérifier Author/Created
        if "Author:" not in docstring:
            warnings.append("Missing Author metadata")
        if "Created:" not in docstring:
            warnings.append("Missing Created metadata")

        # Vérifier tags conditionnels selon GARTNER_TIME
        if result.gartner_tag == "M":  # Migrate
            if "MIGRATION_TARGET:" not in docstring:
                warnings.append("GARTNER_TIME=M but no MIGRATION_TARGET tag")

        if result.gartner_tag == "E":  # Eliminate
            if "DEPRECATION_DATE:" not in docstring:
                warnings.append("GARTNER_TIME=E but no DEPRECATION_DATE tag")
            if "REMOVAL_DATE:" not in docstring:
                warnings.append("GARTNER_TIME=E but no REMOVAL_DATE tag")

        if result.gartner_tag == "T":  # Tolerate
            if "REPLACEMENT:" not in docstring:
                warnings.append("GARTNER_TIME=T but no REPLACEMENT tag suggested")

        result.errors = errors
        result.warnings = warnings
        result.valid = len(errors) == 0

        return result

    def validate_all_files(self, pattern: str = "*.py") -> dict[Path, ValidationResult]:
        """
        Validate tous les fichiers Python du projet.

        Args:
            pattern: Pattern de fichiers à valider (défaut: "*.py")

        Returns:
            Dict avec chemin fichier → résultat validation
        """
        results = {}

        for py_file in self.project_root.rglob(pattern):
            # Ignorer __pycache__, .venv, etc.
            if any(part.startswith(".") or part == "__pycache__" for part in py_file.parts):
                continue

            results[py_file] = self.validate_file(py_file)

        return results

    def print_report(self, results: dict[Path, ValidationResult]):
        """
        Display rapport de validation dans le terminal.

        Args:
            results: Résultats de validation à afficher
        """
        print("\n" + "=" * 80)
        print("📊 GARTNER TIME TAGS VALIDATION REPORT")
        print("=" * 80 + "\n")

        # Statistiques globales
        total_files = len(results)
        valid_files = sum(1 for r in results.values() if r.valid)
        coverage_pct = (valid_files / total_files * 100) if total_files > 0 else 0

        print(f"Total files: {total_files}")
        print(f"Valid files: {valid_files} ({coverage_pct:.1f}%)")
        print(f"Invalid files: {total_files - valid_files}\n")

        # Distribution tags Gartner
        gartner_counts = {"I": 0, "T": 0, "M": 0, "E": 0, "None": 0}
        for result in results.values():
            tag = result.gartner_tag if result.gartner_tag else "None"
            gartner_counts[tag] = gartner_counts.get(tag, 0) + 1

        print("📋 GARTNER TIME Distribution:")
        print(f"  🟢 I (Invest):   {gartner_counts['I']:3d} files")
        print(f"  🟡 T (Tolerate): {gartner_counts['T']:3d} files")
        print(f"  🔵 M (Migrate):  {gartner_counts['M']:3d} files")
        print(f"  🔴 E (Eliminate):{gartner_counts['E']:3d} files")
        print(f"  ⚠️  None:        {gartner_counts['None']:3d} files\n")

        # Fichiers avec erreurs
        files_with_errors = {f: r for f, r in results.items() if r.errors}
        if files_with_errors:
            print("❌ FILES WITH ERRORS:\n")
            for file_path, result in sorted(files_with_errors.items()):
                relative_path = file_path.relative_to(self.project_root)
                print(f"  {relative_path}")
                for error in result.errors:
                    print(f"    ❌ {error}")
                print()

        # Fichiers avec warnings
        files_with_warnings = {f: r for f, r in results.items() if r.warnings}
        if files_with_warnings:
            print("⚠️  FILES WITH WARNINGS:\n")
            for file_path, result in sorted(files_with_warnings.items()):
                relative_path = file_path.relative_to(self.project_root)
                print(f"  {relative_path}")
                for warning in result.warnings:
                    print(f"    ⚠️  {warning}")
                print()

        # Résumé final
        print("=" * 80)
        if valid_files == total_files:
            print("✅ ALL FILES VALID!")
        else:
            print(f"⚠️  {total_files - valid_files} file(s) need attention")
        print("=" * 80 + "\n")

    def generate_html_report(self, results: dict[Path, ValidationResult], output_path: Path):
        """
        Generate rapport HTML de validation.

        Args:
            results: Résultats de validation
            output_path: Chemin du fichier HTML à générer
        """
        html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Gartner TIME Tags Validation Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }
        h1 { color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }
        .stats { display: flex; gap: 20px; margin: 20px 0; }
        .stat-box { flex: 1; padding: 15px; border-radius: 5px; text-align: center; }
        .stat-box.valid { background: #4CAF50; color: white; }
        .stat-box.invalid { background: #f44336; color: white; }
        .stat-box.total { background: #2196F3; color: white; }
        .distribution { margin: 20px 0; }
        .tag-bar { height: 30px; margin: 10px 0; border-radius: 5px; display: flex; align-items: center; padding-left: 10px; color: white; }
        .tag-I { background: #4CAF50; }
        .tag-T { background: #FF9800; }
        .tag-M { background: #2196F3; }
        .tag-E { background: #f44336; }
        .tag-None { background: #9E9E9E; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #4CAF50; color: white; }
        tr:hover { background: #f5f5f5; }
        .error { color: #f44336; }
        .warning { color: #FF9800; }
        .valid { color: #4CAF50; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Gartner TIME Tags Validation Report</h1>
"""
        # Stats
        total_files = len(results)
        valid_files = sum(1 for r in results.values() if r.valid)
        invalid_files = total_files - valid_files
        coverage_pct = (valid_files / total_files * 100) if total_files > 0 else 0

        html += f"""
        <div class="stats">
            <div class="stat-box total">
                <h2>{total_files}</h2>
                <p>Total Files</p>
            </div>
            <div class="stat-box valid">
                <h2>{valid_files}</h2>
                <p>Valid ({coverage_pct:.1f}%)</p>
            </div>
            <div class="stat-box invalid">
                <h2>{invalid_files}</h2>
                <p>Invalid</p>
            </div>
        </div>
"""
        # Distribution
        gartner_counts = {"I": 0, "T": 0, "M": 0, "E": 0, "None": 0}
        for result in results.values():
            tag = result.gartner_tag if result.gartner_tag else "None"
            gartner_counts[tag] = gartner_counts.get(tag, 0) + 1

        html += '<div class="distribution"><h2>📋 GARTNER TIME Distribution</h2>'
        for tag, count in gartner_counts.items():
            pct = (count / total_files * 100) if total_files > 0 else 0
            width = pct
            icon = {"I": "🟢", "T": "🟡", "M": "🔵", "E": "🔴", "None": "⚠️"}[tag]
            label = {
                "I": "Invest",
                "T": "Tolerate",
                "M": "Migrate",
                "E": "Eliminate",
                "None": "No Tag",
            }[tag]
            html += f'<div class="tag-bar tag-{tag}" style="width: {width}%;">{icon} {label}: {count} ({pct:.1f}%)</div>'
        html += "</div>"

        # Table détails
        html += """
        <h2>📄 Detailed Results</h2>
        <table>
            <tr>
                <th>File</th>
                <th>Tag</th>
                <th>Status</th>
                <th>Priority</th>
                <th>Version</th>
                <th>Issues</th>
            </tr>
"""
        for file_path, result in sorted(results.items()):
            relative_path = file_path.relative_to(self.project_root)
            status_class = "valid" if result.valid else "error"
            issues_count = len(result.errors) + len(result.warnings)

            html += f"""
            <tr>
                <td>{relative_path}</td>
                <td>{result.gartner_tag or '-'}</td>
                <td>{result.status or '-'}</td>
                <td>{result.priority or '-'}</td>
                <td>{result.docstring_version or '-'}</td>
                <td class="{status_class}">{issues_count} issue(s)</td>
            </tr>
"""
        html += """
        </table>
    </div>
</body>
</html>
"""
        output_path.write_text(html, encoding="utf-8")
        print(f"✅ HTML report generated: {output_path}")


def main():
    """Point d'entrée du script."""
    parser = argparse.ArgumentParser(description="Validate Gartner TIME tags in Python docstrings")
    parser.add_argument("--file", type=str, help="Validate specific file instead of all project")
    parser.add_argument("--html", type=str, help="Generate HTML report at specified path")
    parser.add_argument(
        "--project-root",
        type=str,
        default="cyclisme_training_logs",
        help="Project root directory (default: cyclisme_training_logs)",
    )

    args = parser.parse_args()

    # Déterminer project root
    if Path(args.project_root).is_absolute():
        project_root = Path(args.project_root)
    else:
        project_root = Path.cwd() / args.project_root

    if not project_root.exists():
        print(f"❌ Project root not found: {project_root}")
        sys.exit(1)

    # Créer validateur
    validator = GartnerTagValidator(project_root)

    # Valider
    if args.file:
        file_path = Path(args.file)
        if not file_path.is_absolute():
            file_path = project_root / file_path

        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            sys.exit(1)

        result = validator.validate_file(file_path)
        results = {file_path: result}
    else:
        results = validator.validate_all_files()

    # Afficher rapport
    validator.print_report(results)

    # Générer HTML si demandé
    if args.html:
        html_path = Path(args.html)
        validator.generate_html_report(results, html_path)

    # Exit code selon résultats
    invalid_count = sum(1 for r in results.values() if not r.valid)
    sys.exit(0 if invalid_count == 0 else 1)


if __name__ == "__main__":
    main()
