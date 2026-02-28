"""UI helper methods for WorkflowCoach."""

import os


class UIHelpersMixin:
    """Terminal UI helpers (clear screen, headers, separators, wait)."""

    def clear_screen(self):
        """Clean l'écran."""
        os.system("clear" if os.name == "posix" else "cls")

    def print_header(self, title, subtitle=None):
        """Display un header stylisé."""
        print("\n" + "=" * 70)

        print(f"  {title}")
        if subtitle:
            print(f"  {subtitle}")
        print("=" * 70 + "\n")

    def print_separator(self):
        """Display un séparateur."""
        print("\n" + "-" * 70 + "\n")

    def wait_user(self, message="Appuyer sur ENTRÉE pour continuer..."):
        """Attendre l'utilisateur."""
        if self.auto_mode:
            print(f"\n[AUTO MODE] Skipping: {message}")
            return
        input(f"\n{message}")
