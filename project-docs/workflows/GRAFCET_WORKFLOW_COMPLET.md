# GRAFCET Workflow Complet - Magma Cycling

**Date** : Mars 2026
**Version** : 2.0
**Architecture** : Post-refactoring Phase 3 (facades + mixins)

---

## 1. Vue d'ensemble systeme

Trois chemins principaux (planning, analyse, servo) convergent vers les facades et leurs mixins.

```mermaid
graph TB
    Start([Utilisateur]) --> Choice{Type d'operation}

    Choice -->|Planning hebdomadaire| WP[WeeklyPlanner]
    Choice -->|Analyse de seance| WC[WorkflowCoach]
    Choice -->|Modifications planning| SM[WorkflowCoach --servo-mode]
    Choice -->|Fin de semaine| EOW[EndOfWeekWorkflow]
    Choice -->|Synchronisation| DS[DailySync]
    Choice -->|Upload workouts| UW[WorkoutUploader]

    subgraph "Facades"
        WP
        WC
        SM
        EOW
        DS
        UW
    end

    subgraph "Mixins Coach (11)"
        WC --> GapDetectionMixin
        WC --> FeedbackMixin
        WC --> AIAnalysisMixin_C[AIAnalysisMixin]
        WC --> SessionDisplayMixin
        WC --> HistoryMixin
        WC --> GitOpsMixin
        WC --> ReconciliationMixin
        WC --> SpecialSessionsMixin
        WC --> ServoControlMixin
        WC --> IntervalsAPIMixin
        WC --> UIHelpersMixin
    end

    subgraph "Mixins Planner (4)"
        WP --> ContextLoadingMixin_P[ContextLoadingMixin]
        WP --> PeriodizationMixin
        WP --> PromptMixin
        WP --> OutputMixin
    end

    subgraph "Mixins EndOfWeek (5)"
        EOW --> AnalysisMixin
        EOW --> EvaluationMixin
        EOW --> AIWorkoutsMixin
        EOW --> UploadMixin_E[UploadMixin]
        EOW --> ArchiveMixin
    end

    subgraph "Mixins Sync (7)"
        DS --> ActivityDetectionMixin
        DS --> SessionUpdatesMixin
        DS --> ServoEvaluationMixin
        DS --> AIAnalysisMixin_S[AIAnalysisMixin]
        DS --> CTLPeaksMixin
        DS --> ReportingMixin
        DS --> ActivityTracker
    end

    subgraph "Mixins Uploader (3)"
        UW --> ValidationMixin
        UW --> ParsingMixin
        UW --> UploadMixin_U[UploadMixin]
    end

    subgraph "Services transverses"
        CT[PlanningControlTower]
        PB[PromptBuilder - build_prompt]
        ES[EventSync - evaluate_sync]
        IC[IntervalsClient]
        AP[AIProviderFactory]
    end

    WC -.-> CT
    WP -.-> PB
    EOW -.-> CT
    UW -.-> ES
    DS -.-> IC
    EOW -.-> AP
```

---

## 2. Pipeline planning hebdomadaire

```mermaid
graph TB
    subgraph "Phase 1 : Chargement contexte"
        Start([poetry run weekly-planner SXXX --start-date YYYY-MM-DD])
        Start --> CL[ContextLoadingMixin.load_athlete_context]
        CL --> CL2[ContextLoadingMixin.load_previous_week_workouts]
        CL2 --> API1[IntervalsClient : GET /wellness]
        API1 --> Metrics[CTL, ATL, TSB, HRV, Weight]
    end

    subgraph "Phase 2 : Periodisation"
        Metrics --> PM[PeriodizationMixin.load_periodization_context]
        PM --> MC[Chargement mesocycle courant]
        MC --> TP[Objectifs phase + contraintes]
    end

    subgraph "Phase 3 : Generation prompt"
        TP --> PR[PromptMixin.generate_planning_prompt]
        PR --> PB[PromptBuilder.build_prompt mission=weekly_planning]
        PB --> Prompt[Prompt complet ~15-20k tokens]
    end

    subgraph "Phase 4 : Sortie + Upload"
        Prompt --> OUT[OutputMixin.copy_to_clipboard]
        OUT --> AI{AI Provider}
        AI -->|clipboard| Clipboard[Copie manuelle vers Claude.ai]
        AI -->|claude_api| DirectAPI[Appel API direct]
        AI -->|mistral_api| MistralAPI[Appel Mistral]

        Clipboard --> Workouts[7 WORKOUT blocks generes]
        DirectAPI --> Workouts
        MistralAPI --> Workouts

        Workouts --> UW2[WorkoutUploader.upload_all]
        UW2 --> VM[ValidationMixin.validate_workout_notation]
        VM --> PM2[ParsingMixin.parse_workouts_file]
        PM2 --> ES2[event_sync.evaluate_sync]
        ES2 --> UM[UploadMixin.upload_workout]
        UM --> API2[IntervalsClient : POST /events]
        API2 --> JSON[Mise a jour week_planning_SXXX.json]
    end

    subgraph "Phase 5 : Statut sessions"
        JSON --> SS[OutputMixin.update_session_status]
        SS --> End([Planning operationnel])
    end
```

---

## 3. Boucle servo-mode

```mermaid
graph TB
    subgraph "Entree"
        Start([poetry run workflow-coach --servo-mode --week-id SXXX])
        Start --> SC[ServoControlMixin]
    end

    subgraph "Lecture planning"
        SC --> CT[PlanningControlTower.read_week]
        CT --> Filter[Filtre sessions date >= today]
        Filter --> HasSessions{Sessions futures ?}
        HasSessions -->|Non| End1([Aucune modification possible])
    end

    subgraph "Prompt AI"
        HasSessions -->|Oui| Format[Format compact planning restant]
        Format --> Build[Construction prompt asservissement]
        Build --> Catalog[Catalogue templates remplacement]
        Build --> Criteria[Criteres decision : HRV, RPE, decouplage, sommeil]
        Build --> JSONSpec[Format JSON attendu]
        Catalog --> PromptReady[Prompt complet]
        Criteria --> PromptReady
        JSONSpec --> PromptReady
    end

    subgraph "Interaction AI"
        PromptReady --> Provider{AI Provider}
        Provider -->|clipboard| Clipboard[pbcopy + pbpaste]
        Provider -->|claude_api| API[Appel API direct]
        Clipboard --> Response[Reponse AI]
        API --> Response
    end

    subgraph "Parsing modifications"
        Response --> Parse[ServoControlMixin.parse_ai_modifications]
        Parse --> Regex[Extraction JSON via regex]
        Regex --> HasMods{Modifications proposees ?}
        HasMods -->|Non| NoChange([Planning maintenu])
    end

    subgraph "Application modifications"
        HasMods -->|Oui| Loop{Pour chaque modification}

        Loop --> Action{Type action}
        Action -->|lighten| Lighten[ServoControlMixin._apply_lighten]
        Action -->|cancel| Cancel[Conversion WORKOUT vers NOTE]
        Action -->|reschedule| Reschedule[Deplacement session]

        Lighten --> Confirm{Confirmation utilisateur}
        Cancel --> Confirm
        Reschedule --> Confirm

        Confirm -->|Non| Skip[Modification ignoree]
        Confirm -->|Oui| Delete[IntervalsClient : DELETE ancien workout]
        Delete --> Upload[IntervalsClient : POST nouveau workout]
        Upload --> Update[PlanningControlTower.modify_week]
        Update --> History[Ajout entree historique + version++]

        Skip --> Next{Autre modification ?}
        History --> Next
        Next -->|Oui| Loop
        Next -->|Non| Save([Planning sauvegarde])
    end
```

---

## 4. Pipeline end-of-week

```mermaid
graph TB
    subgraph "Etape 1 : Analyse semaine"
        Start([poetry run end-of-week --auto])
        Start --> A1[AnalysisMixin._step1_analyze_completed_week]
        A1 --> LoadReports[Chargement rapports quotidiens]
        LoadReports --> LoadWellness[Chargement wellness semaine]
        LoadWellness --> Stats[Calcul statistiques : adherence, TSS, zones]
    end

    subgraph "Etape 2 : Evaluation PID"
        Stats --> E1[EvaluationMixin._step1b_pid_evaluation]
        E1 --> PID[Calcul ecart TSS cible vs realise]
        PID --> FTP[Correction FTP si necessaire]
        FTP --> Reco[Recommandations charge S+1]
    end

    subgraph "Etape 3 : Generation planning AI"
        Reco --> AI1[AIWorkoutsMixin._step2_generate_planning_prompt]
        AI1 --> PB[PromptBuilder.build_prompt mission=weekly_planning]
        PB --> AI2[AIWorkoutsMixin._step3_get_ai_workouts]
        AI2 --> Provider{AI Provider}
        Provider -->|claude_api| Claude[Claude API]
        Provider -->|mistral_api| Mistral[Mistral API]
        Provider -->|clipboard| Manual[Copie manuelle]
        Claude --> Workouts[7 workouts generes]
        Mistral --> Workouts
        Manual --> Workouts
    end

    subgraph "Etape 4-5 : Validation et upload"
        Workouts --> V1[UploadMixin._step4_validate_workouts]
        V1 --> Valid{Validation OK ?}
        Valid -->|Non| Retry[Retry avec autre provider]
        Valid -->|Oui| U1[UploadMixin._step5_upload_to_intervals]
        U1 --> Sync[event_sync.evaluate_sync par session]
        Sync --> API[IntervalsClient : POST /events]
        API --> JSON[UploadMixin._step6_save_planning_json]
    end

    subgraph "Etape 6 : Archive et commit"
        JSON --> AR[ArchiveMixin._step6_archive_and_commit]
        AR --> Archive[Archive rapports S-1]
        Archive --> Git[Git commit + push data repo]
        Git --> Summary[ArchiveMixin._print_success_summary]
        Summary --> End([Semaine bouclée])
    end
```

---

## 5. Pipeline daily-sync

Chaine automatisee quotidienne via LaunchAgents.

```mermaid
graph TB
    subgraph "21:00 Withings pre-sync"
        T1([LaunchAgent 21:00])
        T1 --> WP[withings_presync.sync_withings_to_intervals]
        WP --> Sleep[Sync sommeil hier + aujourd'hui]
        WP --> Weight[Sync poids hier + aujourd'hui]
        Sleep --> Intervals1[IntervalsClient : PUT /wellness]
        Weight --> Intervals1
    end

    subgraph "21:30 Daily Sync"
        Intervals1 -.-> T2([LaunchAgent 21:30])
        T2 --> DS[DailySync.run]
        DS --> AD[ActivityDetectionMixin._detect_duplicate_activities]
        AD --> SU[SessionUpdatesMixin.check_planning_changes]
        SU --> AI[AIAnalysisMixin : analyse automatique]
        AI --> Email[Envoi rapport email]
        AI --> SE[ServoEvaluationMixin.extract_metrics_from_activity]
        SE --> AutoServo{Servo auto active ?}
        AutoServo -->|Oui| Servo[Declenchement servo-mode]
        AutoServo -->|Non| Report[ReportingMixin : generation rapport quotidien]
    end

    subgraph "22:00 Adherence check"
        Report -.-> T3([LaunchAgent 22:00])
        T3 --> Check[Verification adherence planning]
    end

    subgraph "23:00 PID Evaluation"
        Check -.-> T4([LaunchAgent 23:00])
        T4 --> PID[pid_daily_evaluation]
        PID --> CTL[CTLPeaksMixin.analyze_ctl_peaks]
        CTL --> End([Fin chaine quotidienne])
    end
```

---

## 6. Services transverses

```mermaid
graph TB
    subgraph "Control Tower"
        CT[PlanningControlTower]
        CT --> Read[read_week : lecture seule]
        CT --> Modify[modify_week : context manager]
        Modify --> Backup[Backup automatique]
        Modify --> Audit[Audit JSONL : WHO/WHY/WHEN/WHAT]
        Modify --> Permission[Verification permissions]
    end

    subgraph "Prompt Builder"
        PBuild[prompt_builder.build_prompt]
        PBuild --> Mission{Mission}
        Mission -->|daily_feedback| DailyPrompt[Prompt analyse seance]
        Mission -->|weekly_planning| WeeklyPrompt[Prompt planning hebdo]
        PBuild --> Profile[format_athlete_profile]
        PBuild --> Metrics[load_current_metrics : FTP, CTL, ATL]
        PBuild --> System[base_system.txt + mission file]
    end

    subgraph "Event Sync"
        ESSync[event_sync]
        ESSync --> Eval[evaluate_sync : decision sync]
        ESSync --> Hash[calculate_description_hash]
        ESSync --> Time[compute_start_time]
        Eval --> Decision{SyncDecision}
        Decision --> Create[CREATE : nouveau workout]
        Decision --> Update[UPDATE : workout modifie]
        Decision --> Skip[SKIP : deja a jour]
    end

    subgraph "AI Providers"
        APF[AIProviderFactory]
        APF --> Claude[claude_api]
        APF --> Mistral[mistral_api]
        APF --> OpenAI[openai_api]
        APF --> Ollama[ollama]
        APF --> Clip[clipboard]
    end

    subgraph "Intervals.icu Client"
        IC[IntervalsClient]
        IC --> GetAth[get_athlete]
        IC --> GetAct[get_activities]
        IC --> GetWell[get_wellness]
        IC --> GetEvt[get_events]
        IC --> CreateEvt[create_event]
        IC --> UpdateWell[update_wellness]
    end
```

---

## Conventions

- **Nommage noeuds** : `MixinName.method()` (pas de numeros de ligne)
- **Subgraphs** : par phase fonctionnelle
- **Liens pointilles** : dependances inter-services (non bloquantes)
- **Liens pleins** : flux de donnees principal

---

**Date** : Mars 2026
**Version** : 2.0
