# Diagrammes d'activite - Magma Cycling

**Date** : Mars 2026
**Version** : 2.0
**Architecture** : Post-refactoring Phase 3 (facades + mixins)

---

## 1. Flux analyse de seance (WorkflowCoach)

Pipeline complet depuis la detection d'activites jusqu'au commit git.

```mermaid
graph TB
    Start([poetry run workflow-coach])

    subgraph "Detection"
        Start --> Gap[GapDetectionMixin.step_1b_detect_all_gaps]
        Gap --> DetectAct[_detect_unanalyzed_activities]
        DetectAct --> DetectSkip[_detect_skipped_sessions]
        DetectSkip --> DetectRest[_detect_rest_and_cancelled_sessions]
        DetectRest --> Menu[_prompt_user_choice]
        Menu --> Choice{Nombre activites}
        Choice -->|0| NoActivity([Aucune activite a analyser])
        Choice -->|1| Single[Analyse directe]
        Choice -->|2+| Batch[Menu : derniere / choisir / batch]
    end

    subgraph "Feedback"
        Single --> FB[FeedbackMixin.step_2_collect_feedback]
        Batch --> FB
        FB --> Validate[_validate_feedback_collection]
        Validate --> Prepare[_prepare_feedback_context]
        Prepare --> Execute[_execute_feedback_collection]
        Execute --> FBResult{Feedback collecte ?}
        FBResult -->|Non, skip| Analysis
        FBResult -->|Oui| FBData[RPE, sensations, sommeil]
        FBData --> Analysis
    end

    subgraph "Analyse AI"
        Analysis[AIAnalysisMixin.step_3_prepare_analysis]
        Analysis --> DetectWeek[_detect_week_id]
        DetectWeek --> CheckPlan[_check_planning_available]
        CheckPlan --> BuildPrompt[PromptBuilder.build_prompt mission=daily_feedback]
        BuildPrompt --> Provider{AI Provider}
        Provider -->|clipboard| Clipboard[Copie presse-papier]
        Provider -->|claude_api| APICall[Appel API direct]
        Provider -->|mistral_api| MistralCall[Appel Mistral]
        Clipboard --> Display
        APICall --> Display
        MistralCall --> Display
    end

    subgraph "Affichage et validation"
        Display[SessionDisplayMixin.step_4_paste_prompt]
        Display --> Show[step_4b_display_analysis]
        Show --> Validate2[step_5_validate_analysis]
        Validate2 --> Valid{Analyse valide ?}
        Valid -->|Non| Retry([Corriger et relancer])
        Valid -->|Oui| Extract[_extract_metrics_from_analysis]
        Extract --> PostAPI[_post_analysis_to_intervals]
    end

    subgraph "Insertion historique"
        PostAPI --> Insert[HistoryMixin.step_6_insert_analysis]
        Insert --> Preview[_preview_markdowns]
        Preview --> DetectType[_detect_session_type_from_markdown]
        DetectType --> InsertHistory[_insert_to_history]
        InsertHistory --> Export[_export_markdowns]
    end

    subgraph "Git"
        Export --> Git[GitOpsMixin.step_7_git_commit]
        Git --> Commit[_optional_git_commit]
        Commit --> End([Analyse terminee])
    end

    subgraph "Erreurs"
        Analysis -->|API indisponible| ErrAPI([Erreur : verifier credentials])
        Insert -->|Doublon detecte| ErrDup([Erreur : analyse deja inseree])
    end
```

---

## 2. Flux upload workouts (WorkoutUploader)

Pipeline depuis le parsing du fichier workouts jusqu'a l'upload API.

```mermaid
graph TB
    Start([poetry run upload-workouts --week-id SXXX])

    subgraph "Parsing"
        Start --> Source{Source des workouts}
        Source -->|Fichier| ParseFile[ParsingMixin.parse_workouts_file]
        Source -->|Clipboard| ParseClip[ParsingMixin.parse_clipboard]
        ParseFile --> Workouts[Liste de workouts parses]
        ParseClip --> Workouts
    end

    subgraph "Validation"
        Workouts --> Loop{Pour chaque workout}
        Loop --> Validate[ValidationMixin.validate_workout_notation]
        Validate --> ValidResult{Format valide ?}
        ValidResult -->|Non| ErrFormat([Erreur : format invalide - skip])
        ValidResult -->|Oui| Naming[Verification convention SSSS-JJ-TYPE-Nom-V001]
    end

    subgraph "Decision de synchronisation"
        Naming --> Sync[event_sync.evaluate_sync]
        Sync --> Hash[calculate_description_hash]
        Hash --> Time[compute_start_time]
        Time --> Decision{SyncDecision}
        Decision -->|SKIP| AlreadySync([Deja synchronise - skip])
        Decision -->|CREATE| Create[Nouveau workout]
        Decision -->|UPDATE| Update[Workout modifie]
    end

    subgraph "Upload API"
        Create --> Upload[UploadMixin.upload_workout]
        Update --> Upload
        Upload --> Match[_find_matching_event]
        Match --> HasExisting{Event existant ?}
        HasExisting -->|Oui, UPDATE| Delete[IntervalsClient : DELETE ancien]
        HasExisting -->|Non, CREATE| Post[IntervalsClient : POST /events]
        Delete --> Post
        Post --> Result{Upload OK ?}
        Result -->|Non| ErrUpload([Erreur API - log et continue])
        Result -->|Oui| Success[Workout uploade]
    end

    subgraph "Finalisation"
        Success --> Next{Autre workout ?}
        ErrFormat --> Next
        AlreadySync --> Next
        ErrUpload --> Next
        Next -->|Oui| Loop
        Next -->|Non| Summary[upload_all : resume final]
        Summary --> End([Upload termine])
    end
```

---

## 3. Boucle servo-control

Control Tower comme gardien des modifications planning.

```mermaid
graph TB
    Start([Declenchement servo])

    subgraph "Lecture protegee"
        Start --> Read[PlanningControlTower.read_week]
        Read --> Audit1[Audit log : READ operation]
        Audit1 --> Planning[Donnees planning en lecture seule]
        Planning --> Filter[Filtre sessions futures]
        Filter --> HasSessions{Sessions modifiables ?}
        HasSessions -->|Non| End1([Rien a modifier])
    end

    subgraph "Generation recommandations"
        HasSessions -->|Oui| Format[Format compact sessions]
        Format --> Prompt[Construction prompt asservissement]
        Prompt --> AI{AI Provider}
        AI --> Response[Reponse AI avec JSON]
        Response --> Parse[ServoControlMixin.parse_ai_modifications]
        Parse --> Mods{Modifications ?}
        Mods -->|Non| End2([Planning maintenu])
    end

    subgraph "Application avec Control Tower"
        Mods -->|Oui| ForEach{Pour chaque modification}

        ForEach --> Action{Type action}
        Action -->|lighten| Lighten[_apply_lighten]
        Action -->|cancel| Cancel[Conversion WORKOUT vers NOTE avec tag ANNULEE]
        Action -->|reschedule| Reschedule[Deplacement session a nouvelle date]

        Lighten --> Confirm{Confirmation}
        Cancel --> Confirm
        Reschedule --> Confirm

        Confirm -->|Non| Skip[Modification ignoree]
        Confirm -->|Oui| CTModify[PlanningControlTower.modify_week]
    end

    subgraph "Modifications atomiques"
        CTModify --> Backup[Backup automatique planning]
        Backup --> Permission[Verification pas de modification concurrente]
        Permission --> Apply[Application modification JSON]
        Apply --> Version[Increment version]
        Version --> AuditLog[Audit JSONL : MODIFY operation]
        AuditLog --> APISync[IntervalsClient : sync Intervals.icu]
        APISync --> Save[Sauvegarde planning]
    end

    Save --> Next{Autre modification ?}
    Skip --> Next
    Next -->|Oui| ForEach
    Next -->|Non| End3([Modifications appliquees])
```

---

## 4. Pipeline end-of-week autonome

Workflow autonome dimanche soir avec decisions et fallbacks.

```mermaid
graph TB
    Start([poetry run end-of-week --auto --provider claude_api])

    subgraph "Analyse semaine completee"
        Start --> CheckReports{Rapports quotidiens existent ?}
        CheckReports -->|Non| GenReports[Generation rapports manquants]
        CheckReports -->|Oui| LoadReports[AnalysisMixin._step1_analyze_completed_week]
        GenReports --> LoadReports
        LoadReports --> LoadWellness[Chargement wellness semaine]
        LoadWellness --> Stats[Calcul adherence, TSS cumule, zones]
    end

    subgraph "Evaluation PID"
        Stats --> PID[EvaluationMixin._step1b_pid_evaluation]
        PID --> Ecart{Ecart TSS > seuil ?}
        Ecart -->|Oui| Correction[Correction charge recommandee S+1]
        Ecart -->|Non| Nominal[Charge nominale S+1]
        Correction --> Planning
        Nominal --> Planning
    end

    subgraph "Generation planning S+1"
        Planning[AIWorkoutsMixin._step2_generate_planning_prompt]
        Planning --> BuildPrompt[PromptBuilder.build_prompt mission=weekly_planning]
        BuildPrompt --> GetAI[AIWorkoutsMixin._step3_get_ai_workouts]
        GetAI --> Provider{Provider principal}
        Provider -->|claude_api| Claude[Appel Claude API]
        Provider -->|mistral_api| Mistral[Appel Mistral API]
        Claude --> ValidAI{Reponse valide ?}
        Mistral --> ValidAI
        ValidAI -->|Non| Fallback{Fallback provider ?}
        Fallback -->|Oui| Provider
        Fallback -->|Non| ErrAI([Erreur : aucun provider disponible])
        ValidAI -->|Oui| Workouts[7 workouts generes]
    end

    subgraph "Validation et upload"
        Workouts --> Validate[UploadMixin._step4_validate_workouts]
        Validate --> ValidFmt{Format OK ?}
        ValidFmt -->|Non| RetryAI[Retry generation AI]
        RetryAI --> GetAI
        ValidFmt -->|Oui| Upload[UploadMixin._step5_upload_to_intervals]
        Upload --> PerSession{Pour chaque session}
        PerSession --> EvalSync[event_sync.evaluate_sync]
        EvalSync --> SyncDecision{Decision}
        SyncDecision -->|CREATE| Create[IntervalsClient : POST]
        SyncDecision -->|UPDATE| Update[IntervalsClient : PUT]
        SyncDecision -->|SKIP| SkipSync[Deja a jour]
        Create --> UploadResult{OK ?}
        Update --> UploadResult
        UploadResult -->|Non| RetryUpload[Retry avec throttle]
        UploadResult -->|Oui| NextSession{Session suivante ?}
        SkipSync --> NextSession
        RetryUpload --> NextSession
        NextSession -->|Oui| PerSession
        NextSession -->|Non| SaveJSON[_step6_save_planning_json]
    end

    subgraph "Archive et commit"
        SaveJSON --> Archive[ArchiveMixin._step6_archive_and_commit]
        Archive --> ArchiveFiles[Archive rapports dans weekly_reports/]
        ArchiveFiles --> GitCommit[Git commit data repo]
        GitCommit --> GitPush[Git push data repo]
        GitPush --> Summary[_print_success_summary]
        Summary --> End([Semaine S+1 planifiee])
    end
```

---

## Conventions

- **Nommage noeuds** : `MixinName.method()` ou `module.function()`
- **Subgraphs** : par phase fonctionnelle
- **Decisions** : losanges avec conditions explicites
- **Erreurs** : noeuds stadium (arrondi) avec prefix "Erreur"
- **Pas de numeros de ligne** : references par module et methode uniquement

---

**Date** : Mars 2026
**Version** : 2.0
