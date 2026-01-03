#!/usr/bin/env python3
"""
Clipboard-based AI analysis provider.

Provider manuel permettant copy/paste du prompt vers n'importe quel
service IA sans nécessiter de clé API.

Workflow:
1. Génère prompt structuré
2. Copie dans clipboard système (pbcopy/xclip/clip)
3. User paste manuellement dans service IA préféré
4. User copie réponse
5. Paste dans terminal

Examples:
    Use clipboard provider::

        from src.ai.clipboard import ClipboardAnalyzer

        analyzer = ClipboardAnalyzer()
        result = analyzer.analyze_session(prompt)
        # Prompt copié dans clipboard, instructions affichées

Author: Claude Code
Created: 2025-12-09.
"""

import logging
import platform
import subprocess

from .base import AIAnalyzer, AIProvider

logger = logging.getLogger(__name__)


def _copy_to_clipboard_native(text: str) -> bool:
    """Copy text to clipboard using native OS commands.

    Args:
        text: Text to copy

    Returns:
        True if successful, False otherwise

    Notes:
        - macOS: pbcopy
        - Linux: xclip or xsel
        - Windows: clip.
    """
    system = platform.system()

    try:
        if system == "Darwin":  # macOS
            process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE, close_fds=True)
            process.communicate(text.encode("utf-8"))
            return process.returncode == 0

        elif system == "Linux":
            # Try xclip first
            try:
                process = subprocess.Popen(
                    ["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE, close_fds=True
                )
                process.communicate(text.encode("utf-8"))
                if process.returncode == 0:
                    return True
            except FileNotFoundError:
                pass

            # Try xsel as fallback
            try:
                process = subprocess.Popen(
                    ["xsel", "--clipboard", "--input"], stdin=subprocess.PIPE, close_fds=True
                )
                process.communicate(text.encode("utf-8"))
                return process.returncode == 0
            except FileNotFoundError:
                pass

        elif system == "Windows":
            process = subprocess.Popen(["clip"], stdin=subprocess.PIPE, close_fds=True, shell=True)
            process.communicate(text.encode("utf-16"))
            return process.returncode == 0

    except Exception as e:
        logger.debug(f"Native clipboard copy failed: {e}")
        return False

    return False


def _copy_to_clipboard_pyperclip(text: str) -> bool:
    """Copy text to clipboard using pyperclip library.

    Args:
        text: Text to copy

    Returns:
        True if successful, False otherwise.
    """
    try:
        import pyperclip

        pyperclip.copy(text)
        return True
    except Exception as e:
        logger.debug(f"Pyperclip copy failed: {e}")
        return False


def copy_to_clipboard(text: str) -> bool:
    """Copy text to clipboard using best available method.

    Args:
        text: Text to copy

    Returns:
        True if successful, False otherwise

    Notes:
        - Tries native OS commands first (pbcopy, xclip, clip)
        - Falls back to pyperclip if available
        - Returns False if all methods fail.
    """
    # Try native first (more reliable on macOS)
    if _copy_to_clipboard_native(text):
        logger.debug("Copied to clipboard using native commands")
        return True

    # Try pyperclip as fallback
    if _copy_to_clipboard_pyperclip(text):
        logger.debug("Copied to clipboard using pyperclip")
        return True

    logger.warning("All clipboard copy methods failed")
    return False


class ClipboardAnalyzer(AIAnalyzer):
    """Clipboard-based manual AI analysis provider.

    Provider par défaut ne nécessitant pas de clé API.
    Copie le prompt dans le clipboard système pour paste manuel
    dans n'importe quel service IA.

    Attributes:
        provider: AIProvider.CLIPBOARD
        model: "manual" (user choice)

    Examples:
        >>> analyzer = ClipboardAnalyzer()
        >>> result = analyzer.analyze_session(prompt)
        >>> # Prompt copié dans clipboard
        >>> # Instructions affichées pour workflow manuel

    Notes:
        - Gratuit (no API costs)
        - Compatible tous OS (pyperclip)
        - User choisit son AI préféré
        - Workflow interactif simple
    """

    def __init__(self):
        """Initialize clipboard analyzer."""
        super().__init__()
        self.provider = AIProvider.CLIPBOARD
        self.model = "manual"
        logger.info("ClipboardAnalyzer initialized (manual workflow)")

    def analyze_session(self, prompt: str, dataset: dict | None = None) -> str:
        """Copy prompt to clipboard for manual AI analysis.

        Args:
            prompt: Structured session analysis prompt
            dataset: Optional session dataset (unused for clipboard)

        Returns:
            Instructions markdown for manual workflow

        Examples:
            >>> analyzer = ClipboardAnalyzer()
            >>> result = analyzer.analyze_session(prompt)
            >>> print(result)
            # Prompt copié dans clipboard...

        Notes:
            - Copie prompt avec native OS commands (pbcopy, xclip, clip)
            - Fallback pyperclip si disponible
            - Retourne instructions workflow manuel
            - Compatible macOS, Linux, Windows.
        """
        logger.info(f"Copying prompt to clipboard ({len(prompt)} chars)")

        # Try to copy to clipboard
        success = copy_to_clipboard(prompt)

        if success:
            logger.info("Prompt copied to clipboard successfully")
            # Générer instructions utilisateur
            instructions = self._generate_instructions(len(prompt))
            return instructions
        else:
            logger.error("Failed to copy to clipboard with all methods")
            # Fallback: retourner prompt directement si clipboard fail
            return f"""
# ⚠️  Clipboard Error

Could not copy to clipboard (tried native commands and pyperclip).

**macOS Fix**: pbcopy should work by default
**Linux Fix**: Install xclip or xsel: `sudo apt-get install xclip`
**Windows Fix**: clip should work by default

Please manually copy the prompt below:

---

{prompt}

---

Then paste it into your preferred AI service.
"""

    def _generate_instructions(self, prompt_length: int) -> str:
        """Generate user instructions for manual workflow.

        Args:
            prompt_length: Taille du prompt en caractères

        Returns:
            Instructions markdown formatées

        Examples:
            >>> instructions = analyzer._generate_instructions(5000)
            >>> print(instructions[:50])
            '# 📋 Prompt Copié dans Clipboard...'
        """
        return f"""
# 📋 Prompt Copié dans Clipboard ✅

**Taille**: {prompt_length:,} caractères

## 🎯 Workflow Manuel

### Étape 1: Ouvrir Votre Service IA Préféré
Services compatibles:
- Claude.ai (https://claude.ai)
- ChatGPT (https://chat.openai.com)
- Mistral Chat (https://chat.mistral.ai)
- Perplexity (https://perplexity.ai)
- Ou tout autre service IA

### Étape 2: Coller le Prompt
1. Ouvrir nouvelle conversation
2. Coller le prompt (Cmd+V / Ctrl+V)
3. Envoyer pour analyse

### Étape 3: Copier la Réponse
1. Sélectionner l'analyse complète
2. Copier (Cmd+C / Ctrl+C)
3. Retour ici pour sauvegarde

## 💡 Tips
- Tous les services IA majeurs fonctionnent bien
- Gratuit avec la plupart des services (no API key)
- Possibilité follow-up questions pour clarifications
- Format markdown supporté par la plupart

## 📊 Contenu Prompt
Le prompt inclut:
- ✅ Contexte athlète
- ✅ Données activité complètes
- ✅ Plan workout vs réalisé
- ✅ Métriques performance (TSS, IF, NP, HR)
- ✅ Wellness pré/post séance
- ✅ Questions guidance coach

---

**Ready!** Le prompt est dans votre clipboard. Paste-le dans votre service IA maintenant 🚀
"""

    def get_provider_info(self) -> dict:
        """Get clipboard provider info.

        Returns:
            Dict avec provider info

        Examples:
            >>> info = analyzer.get_provider_info()
            >>> print(info)
            {'provider': 'clipboard', 'model': 'manual', 'status': 'ready'}
        """
        return {
            "provider": "clipboard",
            "model": "manual (user choice)",
            "status": "ready",
            "cost": "$0.00",
            "requires_api_key": False,
        }

    def validate_config(self) -> bool:
        """Validate clipboard functionality.

        Returns:
            True if clipboard works, False otherwise

        Examples:
            >>> is_valid = analyzer.validate_config()
            >>> print(is_valid)
            True

        Notes:
            - Tests native commands (pbcopy, xclip, clip)
            - Falls back to pyperclip if available
            - Returns False if all methods fail.
        """
        # Test clipboard with short text
        return copy_to_clipboard("test")
