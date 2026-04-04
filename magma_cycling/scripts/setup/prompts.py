"""Helpers interactifs pour le setup wizard.

Fonctions pures de saisie utilisateur avec validation, messages en francais.
Gerent toutes KeyboardInterrupt -> message propre + sys.exit(0).
"""

import getpass
import os
import sys


def _handle_interrupt():
    """Gere Ctrl+C proprement."""
    print("\n\nConfiguration annulee.")
    sys.exit(0)


def ask_text(label: str, default: str | None = None, required: bool = True) -> str:
    """Demande une saisie texte.

    Args:
        label: Question a afficher.
        default: Valeur par defaut (Entree vide).
        required: Si True, refuse les reponses vides.

    Returns:
        Texte saisi ou valeur par defaut.
    """
    suffix = f" [{default}]" if default else ""
    prompt = f"  {label}{suffix} : "
    while True:
        try:
            value = input(prompt).strip()
        except (KeyboardInterrupt, EOFError):
            _handle_interrupt()
        if not value:
            if default is not None:
                return default
            if not required:
                return ""
            print("    Valeur requise, reessaie.")
            continue
        return value


def ask_int(
    label: str,
    default: int | None = None,
    min_val: int | None = None,
    max_val: int | None = None,
) -> int:
    """Demande un entier avec validation.

    Args:
        label: Question a afficher.
        default: Valeur par defaut.
        min_val: Minimum accepte (inclus).
        max_val: Maximum accepte (inclus).

    Returns:
        Entier valide.
    """
    suffix = f" [{default}]" if default is not None else ""
    prompt = f"  {label}{suffix} : "
    while True:
        try:
            raw = input(prompt).strip()
        except (KeyboardInterrupt, EOFError):
            _handle_interrupt()
        if not raw and default is not None:
            return default
        try:
            value = int(raw)
        except ValueError:
            print("    Entre un nombre entier.")
            continue
        if min_val is not None and value < min_val:
            print(f"    Minimum : {min_val}")
            continue
        if max_val is not None and value > max_val:
            print(f"    Maximum : {max_val}")
            continue
        return value


def ask_float(
    label: str,
    default: float | None = None,
    min_val: float | None = None,
) -> float:
    """Demande un nombre decimal.

    Args:
        label: Question a afficher.
        default: Valeur par defaut.
        min_val: Minimum accepte.

    Returns:
        Float valide.
    """
    suffix = f" [{default}]" if default is not None else ""
    prompt = f"  {label}{suffix} : "
    while True:
        try:
            raw = input(prompt).strip()
        except (KeyboardInterrupt, EOFError):
            _handle_interrupt()
        if not raw and default is not None:
            return default
        try:
            value = float(raw)
        except ValueError:
            print("    Entre un nombre (ex: 72.5).")
            continue
        if min_val is not None and value < min_val:
            print(f"    Minimum : {min_val}")
            continue
        return value


def ask_choice(label: str, options: list[tuple[str, str]], default: int = 0) -> str:
    """Propose un choix multiple.

    Args:
        label: Question a afficher.
        options: Liste de (valeur, libelle_affiche).
        default: Index du choix par defaut (0-based).

    Returns:
        Valeur (premier element du tuple) choisie.
    """
    print(f"  {label}")
    for i, (_, display) in enumerate(options):
        marker = "*" if i == default else " "
        print(f"    {marker} {i + 1}. {display}")
    prompt = f"  Choix [{default + 1}] : "
    while True:
        try:
            raw = input(prompt).strip()
        except (KeyboardInterrupt, EOFError):
            _handle_interrupt()
        if not raw:
            return options[default][0]
        try:
            idx = int(raw) - 1
        except ValueError:
            print(f"    Entre un numero entre 1 et {len(options)}.")
            continue
        if 0 <= idx < len(options):
            return options[idx][0]
        print(f"    Entre un numero entre 1 et {len(options)}.")


def ask_yes_no(label: str, default: bool = True) -> bool:
    """Pose une question oui/non.

    Args:
        label: Question a afficher.
        default: Reponse par defaut.

    Returns:
        True pour oui, False pour non.
    """
    hint = "O/n" if default else "o/N"
    prompt = f"  {label} ({hint}) : "
    while True:
        try:
            raw = input(prompt).strip().lower()
        except (KeyboardInterrupt, EOFError):
            _handle_interrupt()
        if not raw:
            return default
        if raw in ("o", "oui", "y", "yes"):
            return True
        if raw in ("n", "non", "no"):
            return False
        print("    Reponds par o (oui) ou n (non).")


def ask_secret(label: str) -> str:
    """Demande une valeur sensible (masquee).

    Args:
        label: Question a afficher.

    Returns:
        Valeur saisie (non vide).
    """
    prompt = f"  {label} : "
    # getpass ne fonctionne pas dans les .exe PyInstaller sur Windows
    use_getpass = not (os.name == "nt" and getattr(sys, "frozen", False))
    while True:
        try:
            if use_getpass:
                value = getpass.getpass(prompt)
            else:
                value = input(prompt).strip()
        except (KeyboardInterrupt, EOFError):
            _handle_interrupt()
        except Exception:
            try:
                value = input(prompt).strip()
            except (KeyboardInterrupt, EOFError):
                _handle_interrupt()
        if value.strip():
            return value.strip()
        print("    Valeur requise.")


def print_step(num: int, total: int, title: str):
    """Affiche un titre d'etape.

    Args:
        num: Numero de l'etape.
        total: Nombre total d'etapes.
        title: Titre de l'etape.
    """
    print(f"\n── Etape {num}/{total} : {title} ──\n")


def print_success(msg: str):
    """Affiche un message de succes."""
    print(f"  ✓ {msg}")


def print_error(msg: str):
    """Affiche un message d'erreur."""
    print(f"  ✗ {msg}")


def print_info(msg: str):
    """Affiche un message d'information."""
    print(f"  • {msg}")
