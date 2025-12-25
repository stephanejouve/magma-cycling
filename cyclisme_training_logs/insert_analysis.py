#!/usr/bin/env python3
"""
insert_analysis.py - Insère l'analyse de Claude.ai dans workouts-history.md

Ce script :
1. Lit le presse-papier macOS (réponse de Claude.ai)
2. Parse et extrait le bloc markdown d'analyse
3. Insère l'entrée dans logs/workouts-history.md
4. Vérifie avec git diff
5. Propose de commit

Usage:
    python3 cyclisme_training_logs/insert_analysis.py
    python3 cyclisme_training_logs/insert_analysis.py --dry-run  # Test sans modification
    python3 cyclisme_training_logs/insert_analysis.py --file analysis.md  # Depuis fichier
"""

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


class ClipboardReader:
    """Lecteur du presse-papier macOS"""

    @staticmethod
    def read_clipboard():
        """Lire le contenu du presse-papier"""
        try:
            result = subprocess.run(
                ['pbpaste'],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except Exception as e:
            print(f"❌ Erreur lecture presse-papier : {e}")
            return None


class AnalysisParser:
    """Parser pour l'analyse de Claude.ai"""

    @staticmethod
    def extract_markdown_block(text):
        """Extraire le bloc markdown de l'analyse"""

        # Nettoyer le texte
        text = text.strip()

        # Cas 1 : Le texte est déjà un bloc markdown propre (commence par ###)
        if text.startswith('###'):
            return text

        # Cas 2 : Le texte contient un bloc de code markdown (```markdown ... ```)
        markdown_block_pattern = r'```(?:markdown)?\s*\n(.*?)\n```'
        match = re.search(markdown_block_pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Cas 3 : Chercher la première ligne commençant par ###
        lines = text.split('\n')
        start_idx = None
        for i, line in enumerate(lines):
            if line.strip().startswith('###'):
                start_idx = i
                break

        if start_idx is not None:
            # Prendre tout depuis ### jusqu'à la fin ou jusqu'à un marqueur de fin
            remaining = '\n'.join(lines[start_idx:])
            return remaining.strip()

        # Cas 4 : Échec - retourner le texte brut
        print("⚠️  Impossible de détecter automatiquement le bloc markdown")
        print("   Vérification manuelle recommandée")
        return text

    @staticmethod
    def detect_session_type(text):
        """Détecter le type de session (exécutée, repos, annulation)

        Returns:
            str: "executed", "rest", "cancelled", ou "unknown"
        """
        text_lower = text.lower()

        # Détecter repos
        if any(marker in text_lower for marker in ['repos planifié', 'jour de repos', 'rest day']):
            return "rest"

        # Détecter annulation
        if any(marker in text_lower for marker in ['séance annulée', 'session annulée', 'cancelled']):
            return "cancelled"

        # Détecter séance exécutée (présence sections techniques)
        if '#### Exécution' in text or '#### Charge d\'Entraînement' in text:
            return "executed"

        return "unknown"

    @staticmethod
    def count_sessions(text):
        """Compter le nombre de sessions dans le markdown

        Returns:
            int: Nombre de sessions détectées
        """
        # Compter les lignes commençant par ### (titres de session)
        import re
        sessions = re.findall(r'^###\s+', text, re.MULTILINE)
        return len(sessions)

    @staticmethod
    def validate_analysis(text):
        """Valider que le texte est bien une analyse formatée (supporte batch et types multiples)"""

        # Détecter nombre de sessions
        num_sessions = AnalysisParser.count_sessions(text)

        if num_sessions == 0:
            print("⚠️  Aucune session détectée (pas de ### trouvé)")
            return False

        print(f"   📊 {num_sessions} session(s) détectée(s)")

        # Détecter type(s) de session
        session_type = AnalysisParser.detect_session_type(text)
        print(f"   📝 Type détecté : {session_type}")

        # Validation adaptée selon le type
        if session_type == "executed":
            # Validation stricte pour séances exécutées
            required_sections = [
                'Date :',
                '#### Métriques Pré-séance',
                '#### Exécution',
                '#### Exécution Technique',
                '#### Charge d\'Entraînement',
                '#### Validation Objectifs',
                '#### Points d\'Attention',
                '#### Recommandations Progression',
                '#### Métriques Post-séance'
            ]

            missing = []
            for section in required_sections:
                if section not in text:
                    missing.append(section)

            if missing:
                print("⚠️  Sections manquantes dans l'analyse :")
                for m in missing:
                    print(f"   - {m}")
                return False

        elif session_type in ["rest", "cancelled"]:
            # Validation allégée pour repos/annulations
            required_sections = ['Date :']

            missing = []
            for section in required_sections:
                if section not in text:
                    missing.append(section)

            if missing:
                print("⚠️  Sections manquantes (validation allégée) :")
                for m in missing:
                    print(f"   - {m}")
                return False

        else:
            # Type inconnu : validation minimale
            print("⚠️  Type de session inconnu, validation minimale")
            if 'Date :' not in text:
                print("   - Date obligatoire manquante")
                return False

        return True

    @staticmethod
    def extract_date_from_analysis(text):
        """Extraire la date de l'analyse pour détecter les doublons"""
        match = re.search(r'Date\s*:\s*(\d{2}/\d{2}/\d{4})', text)
        if match:
            return match.group(1)
        return None


class WorkoutHistoryManager:
    """Gestionnaire de workouts-history.md"""

    def __init__(self, logs_dir=None, yes_confirm=False):
        """
        Initialize WorkoutHistoryManager.

        Args:
            logs_dir: Legacy parameter, use data repo config instead
            yes_confirm: Auto-confirm all prompts (for non-interactive mode)
        """
        from cyclisme_training_logs.config import get_data_config

        self.yes_confirm = yes_confirm

        # Use data repo config if available
        if logs_dir is None:
            try:
                config = get_data_config()
                self.history_file = config.workouts_history_path
                self.logs_dir = config.data_repo_path
            except FileNotFoundError:
                # Fallback to default logs directory (legacy)
                self.logs_dir = Path.cwd() / 'logs'
                self.history_file = self.logs_dir / "workouts-history.md"
        else:
            # Legacy: explicit logs_dir provided
            self.logs_dir = Path(logs_dir)
            self.history_file = self.logs_dir / "workouts-history.md"

    def read_history(self):
        """Lire le fichier d'historique"""
        if not self.history_file.exists():
            print(f"❌ Fichier non trouvé : {self.history_file}")
            return None

        with open(self.history_file, 'r', encoding='utf-8') as f:
            return f.read()

    def check_duplicate(self, content, analysis_text):
        """Vérifier si une entrée similaire existe déjà"""

        # Extraire le nom de la séance depuis l'analyse
        match = re.search(r'###\s*(.+?)\s*\n', analysis_text)
        if not match:
            return False

        workout_name = match.group(1).strip()

        # Extraire la date
        date = AnalysisParser.extract_date_from_analysis(analysis_text)
        if not date:
            return False

        # Chercher dans le contenu existant
        # Pattern : ### NOM\nDate : DATE
        pattern = rf'###\s*{re.escape(workout_name)}\s*\nDate\s*:\s*{re.escape(date)}'

        if re.search(pattern, content):
            return True

        return False

    def insert_analysis(self, analysis_text):
        """Insérer l'analyse dans workouts-history.md"""

        # Lire le fichier existant
        content = self.read_history()
        if content is None:
            return False

        # Vérifier les doublons
        if self.check_duplicate(content, analysis_text):
            date = AnalysisParser.extract_date_from_analysis(analysis_text)
            print(f"⚠️  Une entrée similaire existe déjà pour la date {date}")
            if self.yes_confirm:
                print("   ✅ Overwrite confirmé (--yes)")
                response = 'y'
            else:
                response = input("   Continuer quand même ? (y/N) : ")
                if response.lower() != 'y':
                    print("❌ Insertion annulée")
                    return False

        # Trouver le point d'insertion (première occurrence de "## Historique")
        insert_marker = "## Historique"
        insert_pos = content.find(insert_marker)

        if insert_pos == -1:
            # Si pas trouvé, insérer à la fin
            print("⚠️  Marqueur '## Historique' non trouvé, insertion à la fin")
            new_content = content + f"\n\n{insert_marker}\n\n{analysis_text}\n\n---\n"
        else:
            # Insérer juste après le marqueur
            # Trouver la fin de la ligne du marqueur
            line_end = content.find('\n', insert_pos)
            if line_end == -1:
                line_end = len(content)

            insertion_point = line_end + 1

            # Construire le nouveau contenu
            new_content = (
                content[:insertion_point] +
                f"\n{analysis_text}\n\n---\n" +
                content[insertion_point:]
            )

        # Écrire le nouveau fichier
        with open(self.history_file, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return True

    def show_diff(self):
        """Afficher le git diff"""
        try:
            result = subprocess.run(
                ['git', 'diff', str(self.history_file)],
                capture_output=True,
                text=True,
                cwd=self.logs_dir.parent
            )
            if result.stdout:
                print("\n" + "=" * 60)
                print("GIT DIFF")
                print("=" * 60)
                print(result.stdout)
            return True
        except Exception as e:
            print(f"⚠️  Impossible d'afficher git diff : {e}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Insérer l'analyse Claude.ai dans workouts-history.md"
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="Mode test : affiche sans modifier"
    )
    parser.add_argument(
        '--file',
        help="Lire depuis un fichier au lieu du presse-papier"
    )
    parser.add_argument(
        '--logs-dir',
        default='logs',
        help="Répertoire des logs (défaut: logs/)"
    )
    parser.add_argument(
        '--yes',
        action='store_true',
        help="Confirmer automatiquement l'insertion (mode non-interactif)"
    )

    args = parser.parse_args()

    print("📋 Insertion de l'analyse dans workouts-history.md")
    print()

    # Lire l'analyse
    if args.file:
        print(f"📂 Lecture depuis {args.file}...")
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"❌ Fichier non trouvé : {args.file}")
            sys.exit(1)
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_text = f.read()
    else:
        print("📋 Lecture du presse-papier...")
        raw_text = ClipboardReader.read_clipboard()
        if not raw_text:
            print("❌ Presse-papier vide")
            sys.exit(1)

    print("   ✅ Contenu récupéré")
    print()

    # Parser l'analyse
    print("🔍 Extraction du bloc markdown...")
    analysis = AnalysisParser.extract_markdown_block(raw_text)

    if not analysis:
        print("❌ Impossible d'extraire l'analyse")
        sys.exit(1)

    print("   ✅ Bloc extrait")
    print()

    # Valider
    print("✓  Validation de l'analyse...")
    num_sessions = AnalysisParser.count_sessions(analysis)

    if not AnalysisParser.validate_analysis(analysis):
        print()
        response = input("   Continuer malgré les avertissements ? (y/N) : ")
        if response.lower() != 'y':
            print("❌ Insertion annulée")
            sys.exit(1)
    else:
        print("   ✅ Format valide")

    # Message si mode batch
    if num_sessions > 1:
        print(f"   🔄 Mode BATCH : {num_sessions} sessions seront insérées ensemble")
    print()

    # Afficher un aperçu
    lines = analysis.split('\n')
    preview_lines = lines[:10] if len(lines) > 10 else lines
    print("📄 Aperçu de l'analyse :")
    print("-" * 60)
    for line in preview_lines:
        print(line)
    if len(lines) > 10:
        print(f"... ({len(lines) - 10} lignes supplémentaires)")
    print("-" * 60)
    print()

    if args.dry_run:
        print("🧪 Mode DRY-RUN : Aucune modification effectuée")
        print("   L'analyse est valide et prête à être insérée")
        sys.exit(0)

    # Confirmer
    if args.yes:
        print("✓ Insertion automatique activée (--yes)")
        response = 'y'
    else:
        response = input("Insérer cette analyse ? (Y/n) : ")
        if response.lower() == 'n':
            print("❌ Insertion annulée")
            sys.exit(0)

    print()

    # Insérer
    print("✍️  Insertion dans workouts-history.md...")
    manager = WorkoutHistoryManager(args.logs_dir, yes_confirm=args.yes)

    if manager.insert_analysis(analysis):
        print("   ✅ Analyse insérée avec succès !")
        print()

        # Afficher le diff
        print("📊 Vérification des modifications...")
        manager.show_diff()

        print()
        print("=" * 60)
        print("✅ INSERTION TERMINÉE")
        print("=" * 60)
        print()
        print("📝 ÉTAPES SUIVANTES :")
        print()
        print("1. Vérifier les modifications :")
        print(f"   git diff {args.logs_dir}/workouts-history.md")
        print()
        print("2. Ajouter au commit :")
        print(f"   git add {args.logs_dir}/workouts-history.md")
        print()
        print("3. Commit :")
        date = AnalysisParser.extract_date_from_analysis(analysis)
        print(f'   git commit -m "Analyse: Séance du {date}"')
        print()
        print("4. Push (optionnel) :")
        print("   git push")
        print()
        print("=" * 60)

    else:
        print("❌ Échec de l'insertion")
        sys.exit(1)


if __name__ == '__main__':
    main()
