# Addendum — Tests renforcés system_prompt & providers

> Complète le plan principal `PROMPT_ENRICH_AI_COACH_CONTEXT.md`
> Le plan initial prévoyait ~28 tests. Cet addendum porte le total à ~42 tests.

---

## Motivation

Le passage du `system_prompt` à travers 5 providers + fallback + clipboard est un point critique.
Un prompt perdu ou mal transmis = analyse IA dégradée silencieusement (pas d'erreur, juste du contenu générique).
Il faut couvrir chaque combinaison pour garantir que le contexte athlète arrive intact au provider final.

---

## Tests additionnels par catégorie

### 1. Rétrocompatibilité providers (5 tests)

Chaque provider appelé SANS system_prompt doit se comporter exactement comme avant.

```
test_claude_analyze_session_without_system_prompt_unchanged
test_mistral_analyze_session_without_system_prompt_uses_default
test_openai_analyze_session_without_system_prompt_no_system_message
test_ollama_analyze_session_without_system_prompt_raw_prompt
test_clipboard_analyze_session_without_system_prompt_prompt_only
```

**Assertion clé :** le mock d'appel API reçoit les mêmes arguments qu'avant le refactoring.

---

### 2. Transmission correcte du system_prompt par provider (5 tests)

Chaque provider appelé AVEC system_prompt l'utilise selon son mécanisme natif.

```
test_claude_system_prompt_passed_as_system_kwarg
  → mock client.messages.create() reçoit kwargs["system"] == system_prompt

test_mistral_system_prompt_replaces_default_system_message
  → messages[0] == {"role": "system", "content": system_prompt}

test_openai_system_prompt_injected_as_first_message
  → messages[0]["role"] == "system" et messages[1]["role"] == "user"

test_ollama_system_prompt_prefixed_with_separator
  → prompt envoyé commence par system_prompt + "\n\n" + user_prompt

test_clipboard_system_prompt_concatenated_readable
  → texte copié contient system_prompt ET user_prompt avec séparateur clair
```

---

### 3. Isolation system vs user (3 tests)

Le system_prompt ne doit pas contaminer le user_prompt et vice-versa.

```
test_claude_system_prompt_not_in_user_messages
  → aucun message avec role="user" ne contient le texte du system_prompt

test_openai_user_prompt_not_in_system_message
  → messages[0]["content"] (system) ne contient pas le workflow_data

test_mistral_system_and_user_are_separate_messages
  → len(messages) >= 2, roles distincts
```

---

### 4. Chaîne de fallback (4 tests)

Le system_prompt doit survivre à chaque étape de la chaîne de fallback.

```
test_fallback_primary_fails_secondary_receives_same_system_prompt
  → provider 1 raise → provider 2 appelé avec system_prompt identique

test_fallback_to_clipboard_preserves_full_prompt
  → provider 1 raise → provider 2 raise → clipboard contient system + user

test_double_fallback_system_prompt_not_lost
  → vérifier que system_prompt n'est pas None au 3ème provider

test_fallback_chain_logs_system_prompt_presence
  → logger.info mentionne que system_prompt est fourni à chaque tentative
```

**Note :** ces tests nécessitent de mocker la chaîne dans le workflow qui gère le fallback (probablement dans `monthly_analysis.py` ou le mécanisme de fallback des providers).

---

### 5. Dégradation gracieuse build_prompt (5 tests)

Le builder doit produire un prompt valide même avec des données partielles.

```
test_build_prompt_without_athlete_context_still_has_base_and_mission
  → athlete_context=None → system_prompt contient base_system + mission, pas de crash

test_build_prompt_partial_metrics_no_crash
  → {"ftp": 223} sans CTL/ATL → format_athlete_profile ne crash pas, affiche ce qui est dispo

test_build_prompt_empty_metrics_graceful
  → {} → system_prompt valide, section métriques absente ou marquée "non disponible"

test_build_prompt_missing_yaml_file_returns_valid_prompt
  → fichier YAML absent → load retourne {} → build_prompt fonctionne

test_build_prompt_corrupted_yaml_returns_empty_context
  → fichier YAML malformé → load retourne {} → pas d'exception
```

---

### 6. Contenu agnostique (3 tests)

Aucune référence à un vendor ou service spécifique dans les prompts générés.

```
test_base_system_no_vendor_references
  → base_system.txt ne contient pas "Zwift", "Withings", "Mistral", "Claude", "OpenAI"

test_mission_files_no_vendor_references
  → les 4 fichiers mission ne contiennent aucune marque commerciale

test_built_system_prompt_no_vendor_references
  → le system_prompt assemblé (avec profil + métriques) ne contient pas de marques
```

---

### 7. Clipboard — qualité du texte copié (3 tests)

Le clipboard est la sortie "humaine" — elle doit être lisible et autosuffisante.

```
test_clipboard_output_has_clear_section_separator
  → le texte contient un séparateur visuel entre contexte coach et données workout
  → ex: "---" ou "## Données d'entraînement" ou équivalent

test_clipboard_output_is_self_contained
  → le texte copié contient : rôle coach, profil athlète, mission, ET données workflow
  → un humain qui lit ce texte comprend le contexte sans information externe

test_clipboard_output_no_api_keys_or_tokens
  → le texte ne contient pas de patterns type "sk-", "api_key", "Bearer", credentials
```

---

## Récapitulatif

| Catégorie | Tests plan initial | Tests addendum | Total |
|-----------|-------------------|----------------|-------|
| Loader YAML | 5 | — | 5 |
| Builder + missions | 14 | — | 14 |
| Dégradation gracieuse builder | — | 5 | 5 |
| Contenu agnostique | — | 3 | 3 |
| Rétrocompatibilité providers | — | 5 | 5 |
| Transmission system_prompt | (inclus dans les 5) | 5 | 5 |
| Isolation system/user | — | 3 | 3 |
| Chaîne de fallback | — | 4 | 4 |
| Clipboard qualité | — | 3 | 3 |
| Monthly analysis intégration | 4 | — | 4 |
| **Total** | **28** | **28** | **~51** |

---

## Priorité d'exécution

Les tests de l'addendum s'insèrent dans les phases existantes :

- **Phase 3 (AI Provider system_prompt)** : ajouter catégories 1, 2, 3 → +13 tests (au lieu de 5)
- **Phase 4 (Migration monthly_analysis)** : ajouter catégorie 4 (fallback) → +4 tests
- **Phase 2 (Prompt infrastructure)** : ajouter catégories 5, 6, 7 → +11 tests

Pas de nouvelle phase — les tests s'intègrent dans le plan existant.
