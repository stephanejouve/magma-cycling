# DIAGRAMMES UML ACTIVITÉ - Corrections P0 Focus

**Date**: 2025-12-21
**Scope**: Workflow génération/upload workouts + servo mode
**Annotations**: fichier:ligne pour chaque point critique

---

## Diagramme 1 : Génération & Upload Workout

### Vue d'ensemble
Ce diagramme montre le flux complet de génération d'un workout hebdomadaire, avec focus sur les 3 points d'injection des corrections P0 (#6, #7, #8).

```mermaid
graph TB
    Start([Utilisateur lance weekly-planner S072])

    subgraph "PHASE 1: Collection Données"
        Start --> Init[__init__ weekly_planner.py:47-65<br/>Initialisation WeeklyPlanner]
        Init --> Run[run weekly_planner.py:484-527<br/>Orchestration workflow]
        Run --> CollectMetrics[collect_current_metrics<br/>weekly_planner.py:67-116<br/>API GET /wellness]
        CollectMetrics --> Metrics{Métriques OK?}
        Metrics -->|Non| ErrorMetrics[Erreur: Credentials invalides]
        Metrics -->|Oui| DataMetrics[CTL, ATL, TSB, HRV, HR]

        DataMetrics --> LoadBilan[load_previous_week_bilan<br/>weekly_planner.py:118-131<br/>Lecture S071 bilan]
        LoadBilan --> BilanExists{Bilan S-1 existe?}
        BilanExists -->|Non| NoBilan[Bilan vide]
        BilanExists -->|Oui| BilanData[Contenu bilan S-1]

        BilanData --> LoadContext[load_context_files<br/>weekly_planner.py:133-171]
        NoBilan --> LoadContext
        LoadContext --> ContextFiles[project_prompt_v2_1<br/>cycling_concepts<br/>protocols]
    end

    subgraph "PHASE 2: Génération Prompt"
        ContextFiles --> GenPrompt[generate_planning_prompt<br/>weekly_planner.py:173-473]

        GenPrompt --> Section1[Contexte Athlète<br/>lines 181-210]
        GenPrompt --> Section2[Période Planning<br/>lines 211-222]
        GenPrompt --> Section3[État Actuel<br/>lines 224-256]

        Section3 --> Section4[Guide Intervals.icu<br/>lines 226-265]

        Section4 --> ValidTypes["⚠️ P0 #8: VALID_TYPES<br/>weekly_planner.py:285<br/>END, INT, FTP, SPR, CLM,<br/>REC, FOR, CAD, TEC, MIX, PDC, TST"]
        ValidTypes:::p0fix

        ValidTypes --> RepFormat["⚠️ P0 #7: RÈGLE CRITIQUE<br/>weekly_planner.py:232-251<br/>Format blocs répétés:<br/>✅ Main set 3x<br/>❌ - 3x 10m 90%"]
        RepFormat:::p0fix

        RepFormat --> Section5[Mission + Contraintes<br/>lines 269-470]
        Section5 --> PromptReady[Prompt complet<br/>~15-20k tokens]
    end

    subgraph "PHASE 3: Interaction AI"
        PromptReady --> Clipboard[copy_to_clipboard<br/>weekly_planner.py:475-482<br/>pbcopy MacOS]
        Clipboard --> UserPaste[Utilisateur colle<br/>dans Claude.ai]
        UserPaste --> ClaudeGen[Claude génère<br/>7 WORKOUT blocks]

        ClaudeGen --> Workout1["=== WORKOUT S072-01-INT... ===<br/>Warmup<br/>- 10m ramp 50-75%<br/>Main set 3x<br/>- 10m 90%<br/>- 4m 62%<br/>Cooldown<br/>- 10m ramp 75-50%<br/>=== FIN WORKOUT ==="]

        Workout1 --> UserCopy[Utilisateur copie workouts]
    end

    subgraph "PHASE 4: Validation Format (Optionnel)"
        UserCopy --> ValidateDecision{Valider format?}
        ValidateDecision -->|Non| ManualUpload
        ValidateDecision -->|Oui| ValidateFormat["intervals_format_validator.py<br/>validate_workout"]

        ValidateFormat --> CheckMarkdown{Contient<br/>markdown?}
        CheckMarkdown -->|Oui| ErrorMD[Erreur: Markdown détecté<br/>**, ###, etc.]
        CheckMarkdown -->|Non| CheckRepFormat

        CheckRepFormat["⚠️ P0 #7 Validation<br/>_check_repetition_format<br/>validator.py:75-111"]:::p0fix
        CheckRepFormat --> RepInInterval{Répétition dans<br/>intervalle?}
        RepInInterval -->|Oui| ErrorRep1["Erreur: '- 3x 10m 90%'<br/>Format incorrect"]
        RepInInterval -->|Non| RepAlone

        RepAlone{Répétition<br/>seule?}
        RepAlone -->|Oui| ErrorRep2["Erreur: '3x' seul<br/>Doit être sur ligne section"]
        RepAlone -->|Non| NonStandard

        NonStandard{Section non<br/>standard?}
        NonStandard -->|Oui| Warn1["⚠️ Warning:<br/>'Test capacité 3x'<br/>Suggérer 'Main set 3x'"]
        NonStandard -->|Non| FormatOK

        Warn1 --> AutoFix[fix_repetition_format<br/>validator.py:118-155<br/>Correction auto]
        AutoFix --> FormatOK

        FormatOK[Format valide]
        ErrorRep1 --> ManualFix[Correction manuelle]
        ErrorRep2 --> ManualFix
        ErrorMD --> ManualFix
        ManualFix --> ValidateFormat
    end

    subgraph "PHASE 5: Upload Manuel Intervals.icu"
        FormatOK --> ManualUpload[Upload manuel<br/>Intervals.icu Web UI]
        ManualUpload --> CreateJSON[Création manuelle<br/>week_planning_S072.json]
        CreateJSON --> JSONStructure{
            week_id: S072
            version: 1
            planned_sessions: []
        }
    end

    subgraph "PHASE 6: Upload Automatique (Servo Mode)"
        UserCopy --> ServoUpload{Servo mode<br/>actif?}
        ServoUpload -->|Non| ManualUpload
        ServoUpload -->|Oui| UploadWorkout[_upload_workout_intervals<br/>workflow_coach.py:307-346]

        UploadWorkout --> LoadCreds[load_credentials<br/>lines 320-325]
        LoadCreds --> CredsOK{Credentials OK?}
        CredsOK -->|Non| ErrorCreds[Erreur: API key manquante]
        CredsOK -->|Oui| InitAPI[IntervalsAPI<br/>lines 327-328]

        InitAPI --> BuildEvent["⚠️ P0 #6: Prepare event<br/>workflow_coach.py:331-336<br/>CORRECTION APPLIQUÉE"]:::p0fix

        BuildEvent --> EventStruct{
            category: WORKOUT
            start_date_local: dateT06:00:00
            name: workout_code
            description: structure ✅
        }

        EventStruct --> APICall[api.create_event<br/>line 339<br/>POST /athlete/ID/events]
        APICall --> APIResult{Upload OK?}
        APIResult -->|Non| ErrorAPI[Erreur upload<br/>line 345<br/>Print erreur]
        APIResult -->|Oui| Success[return True<br/>line 342]
    end

    Success --> End([Fin workflow])
    CreateJSON --> End
    ErrorMetrics --> End
    ErrorCreds --> End
    ErrorAPI --> End

    classDef p0fix fill:#ff6b6b,stroke:#c92a2a,stroke-width:3px,color:#fff
    classDef success fill:#51cf66,stroke:#2f9e44,stroke-width:2px
    classDef error fill:#ffd43b,stroke:#f59f00,stroke-width:2px
```

### Points Critiques - Diagramme 1

#### 🔴 P0 #8: VALID_TYPES (weekly_planner.py:285)
**Injection**: Dans la génération du prompt AI
```python
# Line 285
- **TYPE** : END, INT, FTP, SPR, CLM, REC, FOR, CAD, TEC, MIX, PDC, TST
```

**Impact**: Claude.ai reçoit la liste complète des types valides, évite génération de types inconnus.

---

#### 🔴 P0 #7: Format Blocs Répétés (weekly_planner.py:232-251)
**Injection 1**: Documentation prompt AI (ligne 232)
```python
**RÈGLE CRITIQUE - Blocs répétés** :
Le marqueur (3x) doit être sur la ligne du titre, PAS dans intervalles.

✅ CORRECT:
Main set 3x
- 10m 90%

❌ INCORRECT:
- 3x 10m 90%
Test capacité 3x
```

**Injection 2**: Validation post-génération (optionnel)
```python
# intervals_format_validator.py:75-111
def _check_repetition_format(self, lines):
    # Détecte "- 3x 10m 90%" → ERREUR
    # Détecte "3x" seul → ERREUR
    # Détecte "Test capacité 3x" → WARNING + auto-fix
```

**Impact**:
- Réduit erreurs AI via prompt explicite
- Permet validation avant upload manuel
- Auto-correction des formats corrigibles

---

#### 🔴 P0 #6: Champ API Description (workflow_coach.py:336)
**Injection**: Construction event data
```python
# AVANT (incorrect):
event = {
    "workout_doc": structure  # ❌ Champ inexistant
}

# APRÈS (corrigé):
event = {
    "description": structure  # ✅ Champ API valide
}
```

**Impact**: Upload workouts réussit, Intervals.icu parse correctement le format.

---

## Diagramme 2 : Servo-Mode Modifications Planning

### Vue d'ensemble
Ce diagramme montre le flux servo-mode avec validation format et gestion erreurs upload.

```mermaid
graph TB
    Start([workflow-coach --servo-mode --week-id S072])

    subgraph "PHASE 1: Initialisation"
        Start --> ParseArgs[main<br/>workflow_coach.py:2392-2410<br/>argparse]
        ParseArgs --> Constructor[__init__<br/>lines 42-64<br/>servo_mode=True]
        Constructor --> LoadTemplates["load_workout_templates<br/>lines 91-119<br/>Chargement 6 templates JSON"]

        LoadTemplates --> Template1[recovery_active_30tss<br/>45min Z1-Z2 30 TSS]
        LoadTemplates --> Template6[sweetspot_short_50tss<br/>2x10min 88% 50 TSS]

        Template6 --> ValidateTemplates["⚠️ Validation templates<br/>validate_template_format<br/>Vérifier format Intervals.icu"]:::validation

        ValidateTemplates --> TplMarkdown{Template contient<br/>markdown?}
        TplMarkdown -->|Oui| ErrorTpl[Erreur: Template invalide]
        TplMarkdown -->|Non| TplRepFormat

        TplRepFormat{Format répétitions<br/>correct?}
        TplRepFormat -->|Non| ErrorTpl
        TplRepFormat -->|Oui| TplOK[6 templates valides]

        TplOK --> RunWorkflow[run<br/>lines 2175-2260]
        RunWorkflow --> Step6b[step_6b_servo_control<br/>lines 1855-2024]
    end

    subgraph "PHASE 2: Chargement Planning"
        Step6b --> DetectWeek[Détection week_id<br/>lines 1878-1887<br/>Input utilisateur si absent]
        DetectWeek --> LoadJSON[load_remaining_sessions<br/>lines 121-152<br/>Lecture week_planning_S072.json]

        LoadJSON --> JSONExists{Planning JSON<br/>existe?}
        JSONExists -->|Non| ErrorJSON[Erreur: Fichier absent]
        JSONExists -->|Oui| FilterFuture[Filtre sessions<br/>date >= today]

        FilterFuture --> HasRemaining{Sessions<br/>futures?}
        HasRemaining -->|Non| NoModif[Aucune session à modifier<br/>Fin servo mode]
        HasRemaining -->|Oui| DisplaySessions[Affichage sessions<br/>lines 1907-1912<br/>Format compact]

        DisplaySessions --> UserConfirm{Demander<br/>recommendations AI?<br/>line 1917}
        UserConfirm -->|Non| NoModif
    end

    subgraph "PHASE 3: Génération Prompt Asservissement"
        UserConfirm -->|Oui| FormatContext[format_remaining_sessions_compact<br/>lines 154-183<br/>~150 tokens]

        FormatContext --> BuildPrompt[Construction prompt<br/>lines 1927-1971]
        BuildPrompt --> Header[# ASSERVISSEMENT PLANNING<br/>Contexte: planning restant]
        BuildPrompt --> Catalog["Catalogue templates<br/>lines 1932-1946<br/>RÉCUPÉRATION: 3 templates<br/>ENDURANCE: 2 templates<br/>INTENSITÉ: 1 template"]

        BuildPrompt --> Criteria[Critères décision<br/>lines 1948-1956<br/>HRV < -10%<br/>RPE > 8/10<br/>Découplage > 7.5%]

        BuildPrompt --> JSONFormat["Format JSON attendu<br/>lines 1958-1967<br/>{modifications: [{<br/>  action: 'lighten',<br/>  target_date: 'YYYY-MM-DD',<br/>  template_id: 'recovery_...',<br/>  reason: '...'<br/>}]}"]

        JSONFormat --> PromptReady[Prompt complet<br/>~2000 tokens]
        PromptReady --> Clipboard[pbcopy<br/>lines 1975-1979]
        Clipboard --> Instructions[Affichage instructions<br/>lines 1981-1990]
    end

    subgraph "PHASE 4: Interaction AI & Parsing"
        Instructions --> UserPaste[Utilisateur colle<br/>dans Claude.ai]
        UserPaste --> ClaudeAnalyze[Claude analyse fatigue<br/>+ planning restant]
        ClaudeAnalyze --> ClaudeDecision{Modifications<br/>nécessaires?}

        ClaudeDecision -->|Non| NoModJSON["Réponse:<br/>'Aucune modification nécessaire'<br/>Pas de bloc JSON"]
        ClaudeDecision -->|Oui| GenModJSON["Réponse avec JSON:<br/>```json<br/>{modifications: [...]}<br/>```"]

        GenModJSON --> UserCopyResp[Utilisateur copie réponse<br/>pbpaste lines 2000-2006]
        NoModJSON --> UserCopyResp

        UserCopyResp --> ParseMods["⚠️ parse_ai_modifications<br/>lines 185-211<br/>Extraction regex JSON"]:::validation

        ParseMods --> RegexJSON[Pattern:<br/>```json...```<br/>lines 197-200]
        RegexJSON --> JSONFound{JSON block<br/>trouvé?}

        JSONFound -->|Non| EmptyMods[return []<br/>line 204]
        JSONFound -->|Oui| Deserialize[json.loads<br/>lines 206-208]

        Deserialize --> DeserOK{Parsing OK?}
        DeserOK -->|Non| ErrorParse[JSONDecodeError<br/>line 209-211<br/>return []]
        DeserOK -->|Oui| ModList[Liste modifications]

        EmptyMods --> CheckEmpty
        ErrorParse --> CheckEmpty
        ModList --> CheckEmpty{Liste vide?<br/>line 2015}
    end

    subgraph "PHASE 5: Application Modifications"
        CheckEmpty -->|Oui| NoChange[Planning maintenu<br/>lines 2015-2018]
        CheckEmpty -->|Non| ApplyLoop[apply_planning_modifications<br/>lines 484-509]

        ApplyLoop --> ForEach{Pour chaque<br/>modification}
        ForEach --> ActionType{Action type?<br/>line 499}

        ActionType -->|lighten| ApplyLighten[_apply_lighten<br/>lines 414-482]
        ActionType -->|cancel| TodoCancel[TODO: Implémenter]
        ActionType -->|reschedule| TodoReschedule[TODO: Implémenter]

        ApplyLighten --> ValidateTpl["⚠️ Validation template<br/>lines 421-425<br/>template_id existe?"]:::validation
        ValidateTpl -->|Non| ErrorTpl2[Erreur: Template inconnu<br/>Skip modification]
        ValidateTpl -->|Oui| DisplayMod[Affichage modification<br/>lines 429-432]

        DisplayMod --> UserConfirm2{Confirmation<br/>utilisateur<br/>lines 435-438}
        UserConfirm2 -->|Non| SkipMod[Modification ignorée<br/>line 439]
        UserConfirm2 -->|Oui| ExtractDay

        ExtractDay[_extract_day_number<br/>lines 213-237<br/>Calcul jour 1-7]
        ExtractDay --> GenCode[Génération workout_code<br/>lines 440-445<br/>Pattern: {week_id}-{day:02d}-{TYPE}-{Name}-V001]
    end

    subgraph "PHASE 6: Upload API avec Rollback Potentiel"
        GenCode --> SaveSnapshot["⚠️ Point rollback<br/>État actuel planning"]:::validation

        SaveSnapshot --> GetOldID[_get_workout_id_intervals<br/>lines 239-273<br/>GET /events date=target_date]
        GetOldID --> OldExists{Workout existant<br/>trouvé?}

        OldExists -->|Oui| DeleteOld[_delete_workout_intervals<br/>lines 275-305<br/>DELETE /events/{id}]
        OldExists -->|Non| NoDelete[Aucun workout à supprimer]

        DeleteOld --> DelResult{Suppression OK?}
        DelResult -->|Non| ErrorDel[Erreur suppression<br/>line 304-305<br/>⚠️ Continue quand même]
        DelResult -->|Oui| DeleteSuccess[🗑️ Ancien workout supprimé<br/>line 453]

        NoDelete --> UploadNew
        DeleteSuccess --> UploadNew
        ErrorDel --> UploadNew

        UploadNew["⚠️ P0 #6: _upload_workout_intervals<br/>lines 307-346<br/>POST /events"]:::p0fix

        UploadNew --> BuildEvent2["Prepare event<br/>lines 331-336<br/>{<br/>  category: 'WORKOUT',<br/>  name: code,<br/>  description: structure ✅<br/>}"]

        BuildEvent2 --> APICall2[api.create_event<br/>line 339]
        APICall2 --> UploadResult{Upload OK?<br/>line 342}

        UploadResult -->|Non| ErrorUpload["❌ Erreur upload<br/>line 345<br/>⚠️ PAS DE ROLLBACK<br/>Ancien workout supprimé<br/>Nouveau pas créé"]:::error
        UploadResult -->|Oui| UploadSuccess[✅ Nouveau workout créé<br/>line 460]

        UploadSuccess --> UpdateJSON[_update_planning_json<br/>lines 348-412]
        UpdateJSON --> LoadPlanning[Lecture planning JSON<br/>lines 367-375]
        LoadPlanning --> FindSession[Recherche session<br/>lines 380-387]
        FindSession --> UpdateSession[Modification session<br/>lines 388-403<br/>status='modified'<br/>history.append]
        UpdateSession --> IncrVersion[Incrément version<br/>line 406]
        IncrVersion --> SaveJSON[Sauvegarde JSON<br/>line 408-410]

        SaveJSON --> Complete[✅ Modification appliquée<br/>line 481]
    end

    subgraph "PHASE 7: Boucle Modifications"
        Complete --> NextMod{Autre<br/>modification?}
        ErrorTpl2 --> NextMod
        SkipMod --> NextMod
        TodoCancel --> NextMod
        TodoReschedule --> NextMod

        NextMod -->|Oui| ForEach
        NextMod -->|Non| AllComplete[Toutes modifications traitées]
    end

    AllComplete --> End([Fin servo mode])
    NoChange --> End
    NoModif --> End
    ErrorJSON --> End
    ErrorTpl --> End
    ErrorUpload --> End

    classDef p0fix fill:#ff6b6b,stroke:#c92a2a,stroke-width:3px,color:#fff
    classDef validation fill:#4c6ef5,stroke:#364fc7,stroke-width:3px,color:#fff
    classDef error fill:#ffd43b,stroke:#f59f00,stroke-width:2px
    classDef success fill:#51cf66,stroke:#2f9e44,stroke-width:2px
```

### Points Critiques - Diagramme 2

#### 🔵 Validation Templates (Initialisation)
**Injection**: Après chargement templates, avant utilisation
```python
# workflow_coach.py:109 (à ajouter)
def validate_template_format(self, template: dict) -> bool:
    """Valider format Intervals.icu dans template"""
    from cyclisme_training_logs.intervals_format_validator import IntervalsFormatValidator
    validator = IntervalsFormatValidator()

    format_str = template.get('intervals_icu_format', '')
    is_valid, errors, warnings = validator.validate_workout(format_str)

    if not is_valid:
        print(f"❌ Template {template['id']}: {errors}")
        return False
    return True
```

**Impact**: Templates invalides rejetés au démarrage, pas d'upload de formats incorrects.

---

#### 🔵 Parsing Réponse AI (Extraction JSON)
**Injection**: `parse_ai_modifications()` lines 185-211
```python
# Pattern regex
json_match = re.search(
    r'```json\s*\n(\{.*?"modifications".*?\})\s*\n```',
    ai_response,
    re.DOTALL
)

if not json_match:
    return []  # Aucune modification

data = json.loads(json_match.group(1))
return data.get('modifications', [])
```

**Structure attendue**:
```json
{
  "modifications": [
    {
      "action": "lighten",
      "target_date": "2025-12-18",
      "current_workout": "S072-03-END-Endurance-V001",
      "template_id": "recovery_active_30tss",
      "reason": "HRV -15%, prioriser récupération"
    }
  ]
}
```

**Impact**:
- Parsing robuste avec regex
- Gère absence de JSON (no modifications)
- Gère erreurs JSON (JSONDecodeError)

---

#### 🔵 Validation Template ID
**Injection**: `_apply_lighten()` lines 421-425
```python
template_id = mod['template_id']
if template_id not in self.workout_templates:
    print(f"❌ Template inconnu: {template_id}")
    return  # Skip modification
```

**Impact**: Évite crash si AI propose template inexistant.

---

#### 🔴 P0 #6: Upload API avec Champ Correct
**Injection**: `_upload_workout_intervals()` line 336
```python
event = {
    "category": "WORKOUT",
    "start_date_local": f"{date}T06:00:00",
    "name": code,
    "description": structure  # ✅ CORRIGÉ (était "workout_doc")
}

result = api.create_event(event)
```

**Impact**: Upload réussit avec format Intervals.icu correctement transmis.

---

#### ⚠️ Point de Rollback Manquant (P1 Fix Future)
**Problème**: Si upload nouveau workout échoue, ancien workout déjà supprimé.

**État actuel** (lines 447-464):
```python
# 1. Supprimer ancien
if self._delete_workout_intervals(old_workout_id):
    print("🗑️ Ancien workout supprimé")

# 2. Upload nouveau
if self._upload_workout_intervals(...):
    print("⬆️ Nouveau workout uploadé")
else:
    print("❌ Erreur upload")
    # ⚠️ PAS DE ROLLBACK - ancien workout perdu!
```

**Solution recommandée** (P1):
```python
# Sauvegarder ancien workout avant suppression
snapshot = self._get_workout_data(old_workout_id)

try:
    # Supprimer ancien
    self._delete_workout_intervals(old_workout_id)

    # Upload nouveau
    if not self._upload_workout_intervals(...):
        # Rollback: restaurer ancien
        self._upload_workout_intervals(
            date=snapshot['date'],
            code=snapshot['name'],
            structure=snapshot['description']
        )
        raise Exception("Upload failed, rollback effectué")
except:
    # Rollback automatique en cas d'erreur
```

**Impact**: Évite perte de workout en cas d'échec upload.

---

## Légende Diagrammes

### Couleurs
- 🔴 **Rouge** (`p0fix`): Points d'injection corrections P0 (#6, #7, #8)
- 🔵 **Bleu** (`validation`): Points de validation format/données
- 🟡 **Jaune** (`error`): Chemins d'erreur
- 🟢 **Vert** (`success`): Succès/complétion

### Annotations
- `fichier.py:ligne`: Référence exacte code source
- `lines X-Y`: Plage de lignes pour méthodes
- `⚠️`: Point critique nécessitant attention
- `✅`: Correction appliquée
- `❌`: Erreur détectée

---

## Validation Points - Checklist

### Diagramme 1 (Génération & Upload)
- [ ] P0 #8: VALID_TYPES complets dans prompt (line 285)
- [ ] P0 #7: Format répétitions documenté (lines 232-251)
- [ ] P0 #7: Validation optionnelle avant upload
- [ ] P0 #6: Champ `description` utilisé (line 336)
- [ ] Gestion erreurs credentials API
- [ ] Gestion erreurs upload API

### Diagramme 2 (Servo Mode)
- [ ] Templates validés au chargement
- [ ] Format Intervals.icu vérifié templates
- [ ] Parsing JSON robuste (regex + try/catch)
- [ ] Validation template_id avant application
- [ ] P0 #6: Champ `description` utilisé upload
- [ ] Confirmation utilisateur avant modifications
- [ ] Historique JSON avec timestamp
- [ ] Versioning JSON incrémenté
- [ ] ⚠️ Rollback upload manquant (P1 future)

---

## Utilisation Diagrammes

### Développement
- Référence pour debugging avec numéros de ligne exacts
- Identification rapide points d'injection corrections
- Traçabilité décisions architecture

### Tests
- Validation complète de tous les chemins
- Coverage des cas d'erreur
- Vérification points critiques P0

### Documentation
- Onboarding nouveaux développeurs
- Revue de code structurée
- Maintenance et évolution système

---

## Fichiers Référencés

| Fichier | Lignes Clés | Responsabilité |
|---------|-------------|----------------|
| **weekly_planner.py** | 173-473, 226-265, 285, 475-482 | Génération prompt AI, règles format |
| **workflow_coach.py** | 42-64, 91-119, 185-211, 307-346, 414-482, 1855-2024 | Servo mode, upload API, parsing |
| **intervals_format_validator.py** | 75-111, 118-155 | Validation format, auto-correction |
| **prepare_analysis.py** | 108-146 | API Intervals.icu (create_event) |
| **rest_and_cancellations.py** | 41-42 | VALID_STATUSES, VALID_TYPES |

---

**Date Création**: 2025-12-21
**Mis à Jour**: Après Phase 3 P0 Fixes
**Version**: 1.0
****
