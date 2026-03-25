"""Lecteur du presse-papier macOS."""

import subprocess


class ClipboardReader:
    """Lecteur du presse-papier macOS."""

    @staticmethod
    def read_clipboard():
        """Read le contenu du presse-papier."""
        try:
            result = subprocess.run(["pbpaste"], capture_output=True, text=True, check=True)
            return result.stdout
        except Exception as e:
            print(f"❌ Erreur lecture presse-papier : {e}")
            return None
