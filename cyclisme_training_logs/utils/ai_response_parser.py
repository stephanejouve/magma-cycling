"""
AI response parsing utilities.

Extracted from workflow_coach.py to improve testability and reusability.

Author: Claude Sonnet 4.5
Created: 2026-02-19
"""

import json
import logging
import re

logger = logging.getLogger(__name__)


def parse_ai_modifications(ai_response: str) -> list[dict]:
    """Parse modifications planning depuis réponse AI.

    Gère plusieurs formats:
    - JSON plain: {"modifications": [...]}
    - Markdown: ```json...```
    - Multi-lignes avec whitespace variable

    Args:
        ai_response: Texte réponse AI complet

    Returns:
        list: Modifications à appliquer (vide si aucune)

    Examples:
        >>> # Markdown code block
        >>> response = '''
        ... ```json
        ... {"modifications": [{"action": "lighten", "date": "2026-03-05"}]}
        ... ```
        ... '''
        >>> mods = parse_ai_modifications(response)
        >>> len(mods)
        1

        >>> # Plain JSON
        >>> response = '{"modifications": [{"action": "cancel"}]}'
        >>> mods = parse_ai_modifications(response)
        >>> len(mods)
        1

        >>> # No modifications
        >>> response = "Everything looks good!"
        >>> mods = parse_ai_modifications(response)
        >>> len(mods)
        0
    """
    logger.debug(f"Parsing AI response: {ai_response[:200]}...")

    if not ai_response or not ai_response.strip():
        logger.warning("Empty AI response")
        return []

    # Clean response text
    text = ai_response.strip()

    # Strategy 1: Try to extract from markdown code block
    json_match = re.search(r"```json\s*\n?(\{.*?\})\s*\n?```", text, re.DOTALL | re.MULTILINE)

    if json_match:
        logger.debug("Found JSON in markdown code block")
        json_str = json_match.group(1)
    else:
        # Strategy 2: Try to find JSON object directly (without markdown)
        json_match = re.search(
            r'\{[^{}]*"modifications"[^{}]*\[[^\]]*\][^{}]*\}', text, re.DOTALL | re.MULTILINE
        )

        if json_match:
            logger.debug("Found JSON without markdown")
            json_str = json_match.group(0)
        else:
            # Strategy 3: Look for any JSON-like structure with "modifications" key
            json_match = re.search(r'\{.*?"modifications".*?\}', text, re.DOTALL | re.MULTILINE)

            if json_match:
                logger.debug("Found JSON-like structure with modifications key")
                json_str = json_match.group(0)
            else:
                logger.info("No JSON modifications found in response (normal if no changes needed)")
                return []

    # Parse JSON
    try:
        data = json.loads(json_str)
        logger.debug(f"JSON parsed successfully: {list(data.keys())}")
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        logger.error(f"Failed JSON: {json_str[:200]}")
        print(f"⚠️  JSON modifications invalide : {e}")
        return []

    # Extract modifications list
    modifications = data.get("modifications", [])

    if not isinstance(modifications, list):
        logger.error(f"'modifications' is not a list: {type(modifications)}")
        return []

    logger.info(f"✅ Parsed {len(modifications)} modification(s)")
    return modifications
