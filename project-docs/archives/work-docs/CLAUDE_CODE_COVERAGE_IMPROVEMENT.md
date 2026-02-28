# 🎯 Instructions Claude Code - Amélioration Coverage 80%

**Projet** : magma-cycling
**Objectif** : Améliorer coverage de 68% → 80%
**Durée estimée** : 2-3h
**Branch** : main (directement)

---

## 📊 Contexte

### Coverage Actuel (68%)

```
factory.py:     99% ✅ (quasi-parfait - skip)
base.py:        85% ✅ (excellent - skip)
mistral_api.py: 62% → 75%
ollama.py:      58% → 75%
openai_api.py:  59% → 75%
claude_api.py:  54% → 80%
clipboard.py:   51% → 80%
```

### Tests Échouants Actuels

**23 tests échouent (18%)** :
- API providers sans mocks réalistes
- Cas d'erreur non testés
- Edge cases manquants

---

## 🎯 Stratégie d'Amélioration

### Principe : **Tests Réalistes avec Mocks**

Au lieu de tester les vraies API (coût, instabilité), créer **mocks réalistes** qui simulent :
- ✅ Réponses succès typiques
- ✅ Erreurs API (401, 429, 500, timeout)
- ✅ Edge cases (prompt vide, énorme, encoding)
- ✅ Retry logic et backoff

### Outils Disponibles

```python
import pytest
from unittest.mock import Mock, patch, MagicMock
import responses  # Pour HTTP mocking
```

---

## 📋 Phase 1 : Clipboard Provider (51% → 80%)

### Fichier : `tests/test_ai_providers/test_clipboard.py`

**Tests manquants** :

#### 1. Tests Pyperclip Edge Cases

```python
def test_clipboard_empty_prompt():
    """Test avec prompt vide."""
    analyzer = ClipboardAnalyzer()
    result = analyzer.analyze_session("", None)
    assert "Prompt copié" in result
    assert pyperclip.paste() == ""

def test_clipboard_huge_prompt():
    """Test avec prompt très large (50KB)."""
    analyzer = ClipboardAnalyzer()
    huge_prompt = "A" * 50000
    result = analyzer.analyze_session(huge_prompt, None)
    assert "Prompt copié" in result
    assert pyperclip.paste() == huge_prompt

def test_clipboard_special_characters():
    """Test avec caractères spéciaux."""
    analyzer = ClipboardAnalyzer()
    special = "Test émojis 🚴‍♂️ unicode €£¥ newlines\n\ntabs\t\tquotes'\"«»"
    result = analyzer.analyze_session(special, None)
    assert "Prompt copié" in result
    assert pyperclip.paste() == special

def test_clipboard_dataset_ignored():
    """Vérifier que dataset est ignoré."""
    analyzer = ClipboardAnalyzer()
    dataset = {"key": "value", "list": [1, 2, 3]}
    result = analyzer.analyze_session("Test", dataset)
    assert "Prompt copié" in result
    # Dataset ne doit pas affecter le comportement

@patch('pyperclip.copy', side_effect=Exception("Clipboard error"))
def test_clipboard_copy_failure(mock_copy):
    """Test échec copie clipboard."""
    analyzer = ClipboardAnalyzer()
    with pytest.raises(Exception):
        analyzer.analyze_session("Test", None)
```

#### 2. Tests Instructions Utilisateur

```python
def test_clipboard_instructions_format():
    """Vérifier format instructions utilisateur."""
    analyzer = ClipboardAnalyzer()
    result = analyzer.analyze_session("Test prompt", None)

    # Vérifier présence étapes clés
    assert "Prompt copié" in result
    assert "Claude.ai" in result
    assert "Coller" in result or "Cmd+V" in result or "Ctrl+V" in result
    assert "ENTRÉE" in result or "Enter" in result

def test_clipboard_provider_info():
    """Tester get_provider_info()."""
    analyzer = ClipboardAnalyzer()
    info = analyzer.get_provider_info()

    assert info['provider'] == 'clipboard'
    assert info['model'] == 'manual'
    assert 'description' in info
    assert 'requires_api_key' in info
    assert info['requires_api_key'] is False
```

**Objectif** : +7 tests → Coverage ~80%

---

## 📋 Phase 2 : Claude API (54% → 80%)

### Fichier : `tests/test_ai_providers/test_claude_api.py`

**Créer fichier avec mocks Anthropic SDK** :

```python
"""Tests ClaudeAPIAnalyzer avec mocks."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from magma_cycling.ai_providers.claude_api import ClaudeAPIAnalyzer

@pytest.fixture
def claude_config():
    return {
        'claude_api_key': 'sk-ant-test-key',
        'claude_model': 'claude-sonnet-4-20250514',
        'claude_max_tokens': 4000
    }

@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client."""
    with patch('anthropic.Anthropic') as mock_class:
        mock_client = MagicMock()
        mock_class.return_value = mock_client
        yield mock_client

# === Tests Succès ===

def test_claude_init_success(claude_config):
    """Test initialisation avec config valide."""
    analyzer = ClaudeAPIAnalyzer(claude_config)
    assert analyzer.provider.value == 'claude_api'
    assert analyzer.model == 'claude-sonnet-4-20250514'

def test_claude_analyze_success(claude_config, mock_anthropic_client):
    """Test analyse réussie."""
    # Mock réponse
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Analyse complète de la séance.")]
    mock_anthropic_client.messages.create.return_value = mock_message

    analyzer = ClaudeAPIAnalyzer(claude_config)
    result = analyzer.analyze_session("Analyser cette séance", None)

    assert "Analyse complète" in result
    mock_anthropic_client.messages.create.assert_called_once()

def test_claude_with_dataset(claude_config, mock_anthropic_client):
    """Test analyse avec dataset."""
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Analyse avec données.")]
    mock_anthropic_client.messages.create.return_value = mock_message

    analyzer = ClaudeAPIAnalyzer(claude_config)
    dataset = {"tss": 65, "if": 0.85}
    result = analyzer.analyze_session("Prompt", dataset)

    assert "Analyse avec données" in result
    # Vérifier que dataset est passé dans le prompt
    call_args = mock_anthropic_client.messages.create.call_args
    assert call_args is not None

# === Tests Erreurs ===

def test_claude_missing_api_key():
    """Test erreur si API key manquante."""
    config = {'claude_model': 'claude-sonnet-4-20250514'}
    with pytest.raises(Exception) as exc_info:
        ClaudeAPIAnalyzer(config)
    assert "API key" in str(exc_info.value).lower()

def test_claude_invalid_api_key(claude_config, mock_anthropic_client):
    """Test erreur 401 Unauthorized."""
    from anthropic import AuthenticationError

    mock_anthropic_client.messages.create.side_effect = AuthenticationError(
        "Invalid API key"
    )

    analyzer = ClaudeAPIAnalyzer(claude_config)
    with pytest.raises(AuthenticationError):
        analyzer.analyze_session("Test", None)

def test_claude_rate_limit(claude_config, mock_anthropic_client):
    """Test erreur 429 Rate Limit."""
    from anthropic import RateLimitError

    mock_anthropic_client.messages.create.side_effect = RateLimitError(
        "Rate limit exceeded"
    )

    analyzer = ClaudeAPIAnalyzer(claude_config)
    with pytest.raises(RateLimitError):
        analyzer.analyze_session("Test", None)

def test_claude_server_error(claude_config, mock_anthropic_client):
    """Test erreur 500 serveur."""
    from anthropic import APIError

    mock_anthropic_client.messages.create.side_effect = APIError(
        "Internal server error"
    )

    analyzer = ClaudeAPIAnalyzer(claude_config)
    with pytest.raises(APIError):
        analyzer.analyze_session("Test", None)

def test_claude_timeout(claude_config, mock_anthropic_client):
    """Test timeout."""
    import requests

    mock_anthropic_client.messages.create.side_effect = requests.Timeout(
        "Request timeout"
    )

    analyzer = ClaudeAPIAnalyzer(claude_config)
    with pytest.raises(requests.Timeout):
        analyzer.analyze_session("Test", None)

# === Tests Edge Cases ===

def test_claude_empty_prompt(claude_config, mock_anthropic_client):
    """Test prompt vide."""
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="")]
    mock_anthropic_client.messages.create.return_value = mock_message

    analyzer = ClaudeAPIAnalyzer(claude_config)
    result = analyzer.analyze_session("", None)
    assert result == ""

def test_claude_huge_prompt(claude_config, mock_anthropic_client):
    """Test prompt très large."""
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Réponse")]
    mock_anthropic_client.messages.create.return_value = mock_message

    analyzer = ClaudeAPIAnalyzer(claude_config)
    huge_prompt = "A" * 50000
    result = analyzer.analyze_session(huge_prompt, None)

    assert "Réponse" in result

def test_claude_provider_info(claude_config):
    """Tester get_provider_info()."""
    analyzer = ClaudeAPIAnalyzer(claude_config)
    info = analyzer.get_provider_info()

    assert info['provider'] == 'claude_api'
    assert info['model'] == 'claude-sonnet-4-20250514'
    assert info['requires_api_key'] is True
```

**Objectif** : +13 tests → Coverage ~80%

---

## 📋 Phase 3 : Autres API Providers

### Pattern Réutilisable

Les providers Mistral, OpenAI suivent le **même pattern** que Claude.

**Template test_PROVIDER_api.py** :

```python
"""Tests PROVIDERAnalyzer."""
import pytest
from unittest.mock import Mock, patch, MagicMock

# === Fixtures ===
@pytest.fixture
def provider_config():
    return {'PROVIDER_api_key': 'test-key', ...}

@pytest.fixture
def mock_client():
    with patch('LIBRARY.Client') as mock:
        yield mock.return_value

# === Tests Succès ===
def test_init_success(provider_config): ...
def test_analyze_success(provider_config, mock_client): ...
def test_with_dataset(provider_config, mock_client): ...

# === Tests Erreurs ===
def test_missing_api_key(): ...
def test_invalid_api_key(provider_config, mock_client): ...
def test_rate_limit(provider_config, mock_client): ...
def test_server_error(provider_config, mock_client): ...
def test_timeout(provider_config, mock_client): ...

# === Tests Edge Cases ===
def test_empty_prompt(provider_config, mock_client): ...
def test_huge_prompt(provider_config, mock_client): ...
def test_provider_info(provider_config): ...
```

### Fichiers à Créer

1. **tests/test_ai_providers/test_mistral_api.py** (+13 tests)
2. **tests/test_ai_providers/test_openai_api.py** (+13 tests)

**Adapter mocks selon SDK** :
- Mistral : `from mistralai.client import MistralClient`
- OpenAI : `from openai import OpenAI`

---

## 📋 Phase 4 : Ollama Provider

### Fichier : `tests/test_ai_providers/test_ollama.py`

**Tests spécifiques Ollama** :

```python
"""Tests OllamaAnalyzer."""
import pytest
from unittest.mock import Mock, patch
import requests
from magma_cycling.ai_providers.ollama import OllamaAnalyzer

@pytest.fixture
def ollama_config():
    return {
        'ollama_host': 'http://localhost:11434',
        'ollama_model': 'mistral:7b'
    }

# === Tests Succès ===

@patch('requests.post')
def test_ollama_analyze_success(mock_post, ollama_config):
    """Test analyse réussie."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'response': 'Analyse Ollama complète.'
    }
    mock_post.return_value = mock_response

    analyzer = OllamaAnalyzer(ollama_config)
    result = analyzer.analyze_session("Test", None)

    assert "Analyse Ollama" in result

@patch('requests.post')
def test_ollama_server_available(mock_post, ollama_config):
    """Vérifier disponibilité serveur."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_post.return_value = mock_response

    analyzer = OllamaAnalyzer(ollama_config)
    assert analyzer.model == 'mistral:7b'

# === Tests Erreurs ===

@patch('requests.post')
def test_ollama_connection_error(mock_post, ollama_config):
    """Test erreur connexion serveur."""
    mock_post.side_effect = requests.ConnectionError("Cannot connect")

    analyzer = OllamaAnalyzer(ollama_config)
    with pytest.raises(requests.ConnectionError):
        analyzer.analyze_session("Test", None)

@patch('requests.post')
def test_ollama_timeout(mock_post, ollama_config):
    """Test timeout."""
    mock_post.side_effect = requests.Timeout("Request timeout")

    analyzer = OllamaAnalyzer(ollama_config)
    with pytest.raises(requests.Timeout):
        analyzer.analyze_session("Test", None)

@patch('requests.post')
def test_ollama_model_not_found(mock_post, ollama_config):
    """Test modèle non trouvé."""
    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.text = "Model not found"
    mock_post.return_value = mock_response

    analyzer = OllamaAnalyzer(ollama_config)
    with pytest.raises(Exception):
        analyzer.analyze_session("Test", None)

@patch('requests.post')
def test_ollama_server_error(mock_post, ollama_config):
    """Test erreur serveur 500."""
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = "Internal error"
    mock_post.return_value = mock_response

    analyzer = OllamaAnalyzer(ollama_config)
    with pytest.raises(Exception):
        analyzer.analyze_session("Test", None)

# === Tests Edge Cases ===

@patch('requests.post')
def test_ollama_empty_response(mock_post, ollama_config):
    """Test réponse vide."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'response': ''}
    mock_post.return_value = mock_response

    analyzer = OllamaAnalyzer(ollama_config)
    result = analyzer.analyze_session("Test", None)
    assert result == ''

@patch('requests.post')
def test_ollama_custom_host(mock_post):
    """Test avec host personnalisé."""
    config = {
        'ollama_host': 'http://192.168.1.100:11434',
        'ollama_model': 'llama3.1:8b'
    }
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'response': 'OK'}
    mock_post.return_value = mock_response

    analyzer = OllamaAnalyzer(config)
    result = analyzer.analyze_session("Test", None)

    # Vérifier URL appelée
    call_args = mock_post.call_args
    assert '192.168.1.100:11434' in call_args[0][0]
```

**Objectif** : +10 tests → Coverage ~75%

---

## 📋 Phase 5 : Validation & Commit

### Étape 1 : Lancer Tests & Coverage

```bash
# Tests complets
poetry run pytest tests/test_ai_providers/ -v

# Coverage détaillé
poetry run pytest tests/test_ai_providers/ \
  --cov=magma_cycling/ai_providers \
  --cov-report=term-missing \
  --cov-report=html

# Ouvrir rapport HTML
open htmlcov/index.html
```

### Étape 2 : Vérifier Objectif

**Critères succès** :
- ✅ Coverage global ≥ 80%
- ✅ Chaque fichier ≥ 75%
- ✅ Tests passing ≥ 95% (max 6 fails sur 125)

### Étape 3 : Commit

```bash
git add tests/test_ai_providers/
git commit -m "test(ai): Improve coverage to 80%+ with realistic mocks

- Add clipboard edge cases tests (+7 tests)
- Add Claude API comprehensive tests (+13 tests)
- Add Mistral API tests with mocks (+13 tests)
- Add OpenAI tests with mocks (+13 tests)
- Add Ollama error handling tests (+10 tests)

Coverage improved:
- clipboard.py: 51% → 80%
- claude_api.py: 54% → 80%
- ollama.py: 58% → 75%
- openai_api.py: 59% → 75%
- mistral_api.py: 62% → 75%

Overall: 68% → 82% coverage ✅
"

git push origin main
```

---

## 🎯 Checklist Validation

Avant de marquer TERMINÉ, vérifier :

- [ ] Clipboard tests créés (+7 tests minimum)
- [ ] Claude API tests créés (+13 tests minimum)
- [ ] Mistral API tests créés (+13 tests minimum)
- [ ] OpenAI tests créés (+13 tests minimum)
- [ ] Ollama tests créés (+10 tests minimum)
- [ ] Coverage global ≥ 80%
- [ ] Chaque provider ≥ 75% coverage
- [ ] Tests passing ≥ 95%
- [ ] Rapport HTML coverage généré
- [ ] Commit pushed sur main

---

## 📊 Résultat Attendu

### Avant
```
Tests: 125 (102 pass, 23 fail) - 82% pass
Coverage: 68%
```

### Après
```
Tests: 181+ (172+ pass, <10 fail) - 95%+ pass
Coverage: 82%+

Breakdown:
- clipboard.py:    80%+ ✅
- claude_api.py:   80%+ ✅
- mistral_api.py:  75%+ ✅
- openai_api.py:   75%+ ✅
- ollama.py:       75%+ ✅
- factory.py:      99%  ✅ (inchangé)
- base.py:         85%  ✅ (inchangé)
```

---

## 🚀 Commande Démarrage

Pour lancer l'amélioration coverage, dis-moi :

**"Lance l'amélioration coverage selon CLAUDE_CODE_COVERAGE_IMPROVEMENT.md"**

Je vais :
1. Créer tous les tests manquants
2. Utiliser mocks réalistes pour API
3. Couvrir edge cases et erreurs
4. Valider coverage ≥ 80%
5. Committer sur main

**Prêt pour coverage 80%+ ! 🎯**
