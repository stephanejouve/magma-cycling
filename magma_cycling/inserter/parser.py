"""Parsing et validation des analyses markdown."""

import re


class AnalysisParser:
    """Parse pour l'analyse de Claude.ai."""

    @staticmethod
    def extract_markdown_block(text):
        """Extract le bloc markdown de l'analyse."""
        # Nettoyer le texte

        text = text.strip()

        # Cas 1 : Le texte est déjà un bloc markdown propre (commence par ###)
        if text.startswith("###"):
            return text

        # Cas 2 : Le texte contient un bloc de code markdown (```markdown ... ```)
        markdown_block_pattern = r"```(?:markdown)?\s*\n(.*?)\n```"
        match = re.search(markdown_block_pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Cas 3 : Chercher la première ligne commençant par ###
        lines = text.split("\n")
        start_idx = None
        for i, line in enumerate(lines):
            if line.strip().startswith("###"):
                start_idx = i
                break

        if start_idx is not None:
            # Prendre tout depuis ### jusqu'à la fin ou jusqu'à un marqueur de fin
            remaining = "\n".join(lines[start_idx:])
            return remaining.strip()

        # Cas 4 : Échec - retourner le texte brut
        print("⚠️  Impossible de détecter automatiquement le bloc markdown")
        print("   Vérification manuelle recommandée")
        return text

    @staticmethod
    def detect_session_type(text):
        """Détecter le type de session (exécutée, repos, annulation).

        Returns:
            str: "executed", "rest", "cancelled", ou "unknown"
        """
        text_lower = text.lower()

        # Détecter repos
        if any(marker in text_lower for marker in ["repos planifié", "jour de repos", "rest day"]):
            return "rest"

        # Détecter annulation
        if any(
            marker in text_lower for marker in ["séance annulée", "session annulée", "cancelled"]
        ):
            return "cancelled"

        # Détecter séance exécutée (présence sections techniques)
        if "#### Exécution" in text or "#### Charge d'Entraînement" in text:
            return "executed"

        return "unknown"

    @staticmethod
    def count_sessions(text):
        """Compter le nombre de sessions dans le markdown.

        Returns:
            int: Nombre de sessions détectées.
        """
        # Compter les lignes commençant par ### (titres de session)

        sessions = re.findall(r"^###\s+", text, re.MULTILINE)
        return len(sessions)

    @staticmethod
    def validate_analysis(text):
        """Validate que le texte est bien une analyse formatée (supporte batch et types multiples)."""
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
                "Date :",
                "#### Métriques Pré-séance",
                "#### Exécution",
                "#### Exécution Technique",
                "#### Charge d'Entraînement",
                "#### Validation Objectifs",
                "#### Points d'Attention",
                "#### Recommandations Progression",
                "#### Métriques Post-séance",
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
            required_sections = ["Date :"]

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
            if "Date :" not in text:
                print("   - Date obligatoire manquante")
                return False

        return True

    @staticmethod
    def extract_date_from_analysis(text):
        """Extract la date de l'analyse pour détecter les doublons."""
        match = re.search(r"Date\s*:\s*(\d{2}/\d{2}/\d{4})", text)

        if match:
            return match.group(1)
        return None
