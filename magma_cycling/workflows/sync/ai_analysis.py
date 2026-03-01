"""AIAnalysisMixin — AI-powered activity analysis and history management."""

from datetime import date, timedelta

from magma_cycling.planning.control_tower import planning_tower


class AIAnalysisMixin:
    """Mixin for AI analysis of activities."""

    def _extract_existing_analysis(
        self, activity_name: str, activity_id: str, activity_date_str: str
    ) -> str | None:
        """
        Check if analysis already exists in workouts-history.md and extract it.

        Args:
            activity_name: Name of the activity
            activity_id: Activity ID (e.g., i122040268)
            activity_date_str: Date in format DD/MM/YYYY

        Returns:
            Existing analysis text or None if not found
        """
        if not self.history_manager:
            return None

        try:
            history_content = self.history_manager.read_history()
            if not history_content:
                return None

            # Look for the activity entry
            import re

            # Pattern: ### ACTIVITY_NAME\nID : ACTIVITY_ID\nDate : DATE
            # This ensures we match the exact activity even if multiple activities
            # have the same name on the same day
            pattern = (
                rf"###\s*{re.escape(activity_name)}\s*\n"
                rf"ID\s*:\s*{re.escape(activity_id)}\s*\n"
                rf"Date\s*:\s*{re.escape(activity_date_str)}"
            )
            match = re.search(pattern, history_content)

            if not match:
                return None

            # Extract the full entry (from ### to next ### or end)
            start_pos = match.start()
            next_entry = re.search(r"\n###\s+", history_content[start_pos + 1 :])

            if next_entry:
                end_pos = start_pos + 1 + next_entry.start()
                analysis = history_content[start_pos:end_pos].strip()
            else:
                analysis = history_content[start_pos:].strip()

            return analysis

        except Exception as e:
            print(f"     ⚠️  Erreur extraction analyse existante: {e}")
            return None

    def analyze_activity(self, activity: dict) -> str | None:
        """
        Generate or retrieve AI analysis for an activity.

        Checks if analysis already exists in workouts-history.md:
        - If yes: extracts and returns existing analysis
        - If no: generates new analysis, inserts into history, and returns it

        Args:
            activity: Activity dict with id and other metadata

        Returns:
            Analysis text or None if failed
        """
        if not self.enable_ai_analysis or not self.ai_analyzer:
            return None

        try:
            # Use activity ID directly (activity dict, not event dict)
            activity_id = activity.get("id")
            if not activity_id:
                print(f"  ⚠️  Pas d'ID activité pour {activity.get('name', 'Unknown')}")
                return None

            activity_name = activity.get("name", "")
            print(f"  🔍 Vérification analyse existante pour {activity_name}...")

            # Extract date from activity
            activity_date = date.fromisoformat(activity["start_date_local"].split("T")[0])
            activity_date_str = activity_date.strftime("%d/%m/%Y")

            # Check if analysis already exists
            existing_analysis = self._extract_existing_analysis(
                activity_name, activity_id, activity_date_str
            )

            if existing_analysis:
                print("     ✅ Analyse existante trouvée dans workouts-history.md")
                return existing_analysis

            print(f"  🤖 Génération nouvelle analyse AI pour {activity_name}...")

            # Add is_strava flag (required by PromptGenerator)
            activity["is_strava"] = activity.get("source") == "STRAVA"

            # Get wellness data (pre and post)
            activity_date_str = activity["start_date_local"].split("T")[0]

            # Get pre-workout wellness
            try:
                wellness_data = self.client.get_wellness(
                    oldest=activity_date_str, newest=activity_date_str
                )
                wellness_pre = wellness_data[0] if wellness_data else None
            except Exception:
                wellness_pre = None

            # Get post-workout wellness (may not exist yet for today's workout)
            try:
                activity_date = date.fromisoformat(activity_date_str)
                next_day = activity_date + timedelta(days=1)
                next_day_str = next_day.isoformat()
                wellness_data = self.client.get_wellness(oldest=next_day_str, newest=next_day_str)
                wellness_post = wellness_data[0] if wellness_data else None
            except Exception:
                wellness_post = None

            # Load athlete context and recent workouts
            athlete_context = self.prompt_generator.load_athlete_context()
            recent_workouts = self.prompt_generator.load_recent_workouts(limit=5)

            # Format activity data for prompt generation
            activity_data = self.prompt_generator.format_activity_data(activity)

            # Load periodization context for strategic coherence
            periodization_context = self.prompt_generator.load_periodization_context(wellness_pre)

            # Get planned workout if available (for adherence tracking)
            planned_workout = None
            try:
                activity_datetime = date.fromisoformat(activity_date_str)
                planned_workout = self.client.get_planned_workout(activity_id, activity_datetime)
            except Exception:
                pass  # No planned workout available

            # Get session prescription from local planning JSON
            session_prescription = None
            if "-" in activity_name:
                parts = activity_name.split("-")
                if len(parts) >= 2 and parts[0].startswith("S") and len(parts[0]) == 4:
                    _week_id = parts[0]
                    _session_id = f"{parts[0]}-{parts[1]}"
                    try:
                        plan = planning_tower.read_week(_week_id)
                        for s in plan.planned_sessions:
                            if s.session_id == _session_id:
                                session_prescription = s.description
                                break
                    except Exception:
                        pass  # Planning not found — skip

            # Generate complete prompt
            prompt = self.prompt_generator.generate_prompt(
                activity_data=activity_data,
                wellness_pre=wellness_pre,
                wellness_post=wellness_post,
                athlete_context=athlete_context,
                recent_workouts=recent_workouts,
                athlete_feedback=None,  # No feedback in automated mode
                planned_workout=planned_workout,
                cycling_concepts=None,
                periodization_context=periodization_context,
                session_prescription=session_prescription,
            )

            # Get AI analysis
            analysis = self.ai_analyzer.analyze_session(prompt)

            if analysis:
                print(f"     ✅ Analyse générée ({len(analysis)} caractères)")

                # Capture adherence data if planned workout exists
                if planned_workout:
                    try:
                        from magma_cycling.analyzers.adherence_storage import (
                            AdherenceStorage,
                        )
                        from magma_cycling.analyzers.adherence_tracker import (
                            AdherenceTracker,
                        )

                        tracker = AdherenceTracker()
                        adherence_data = tracker.calculate_session_adherence(
                            activity, planned_workout
                        )

                        # Extract week ID from activity name (e.g., "S082-01-END-..." -> "S082")
                        week_id = None
                        if "-" in activity_name:
                            parts = activity_name.split("-")
                            if parts[0].startswith("S") and len(parts[0]) == 4:
                                week_id = parts[0]

                        if week_id and adherence_data.get("has_plan"):
                            storage = AdherenceStorage()
                            storage.save_session_adherence(
                                activity_id=activity_id,
                                week_id=week_id,
                                date=activity_date_str,
                                adherence_data=adherence_data,
                            )
                            print(
                                f"     📊 Adhérence capturée: TSS {adherence_data.get('tss_adherence', 0):.0%}"
                            )

                    except Exception as e:
                        print(f"     ⚠️  Impossible de capturer adhérence : {e}")

                # Insert analysis into workouts-history.md
                print("     📝 Insertion dans workouts-history.md...")
                try:
                    if self.history_manager.insert_analysis(analysis):
                        print("     ✅ Analyse insérée dans workouts-history.md")
                    else:
                        print("     ⚠️  Échec insertion (analyse utilisée quand même)")
                except Exception as e:
                    print(f"     ⚠️  Erreur insertion workouts-history.md: {e}")
                    # Continue anyway - we still have the analysis for email

                return analysis
            else:
                print("     ⚠️  Échec génération analyse")
                return None

        except Exception as e:
            print(f"     ❌ Erreur analyse AI: {e}")
            return None
