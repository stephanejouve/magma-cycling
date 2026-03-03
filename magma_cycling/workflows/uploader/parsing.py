"""Parsing mixin for WorkoutUploader."""

import re
from datetime import timedelta
from pathlib import Path


class ParsingMixin:
    """Parsing fichier et clipboard."""

    def parse_workouts_file(self, filepath: Path) -> list[dict]:
        """Parse un fichier contenant les workouts."""
        print(f"\n📄 Lecture fichier : {filepath}")

        if not filepath.exists():
            print(f"❌ Fichier non trouvé : {filepath}")
            return []

        content = filepath.read_text(encoding="utf-8")
        pattern = r"=== WORKOUT (.*?) ===\n(.*?)\n=== FIN WORKOUT ==="
        matches = re.findall(pattern, content, re.DOTALL)

        # Mode single workout : utiliser date exacte
        single_workout_mode = len(matches) == 1
        if single_workout_mode:
            print("  ℹ️  Mode single workout détecté - utilisation date exacte")

        workouts = []
        for workout_name, workout_content in matches:
            # Support format standard (S081-05) et double séance (S081-06a, S081-06b)
            day_match = re.search(r"-(\d{2})([a-z]?)-", workout_name)
            if not day_match:
                print(f"⚠️ Format invalide : {workout_name}")
                continue

            day_num = int(day_match.group(1))
            suffix = day_match.group(2)  # 'a', 'b', ou vide ''

            # Si single workout, utiliser start_date directement
            if single_workout_mode:
                workout_date = self.start_date
                print(
                    f"  📌 Workout sera uploadé le {workout_date.strftime('%d/%m/%Y')} (date explicite)"
                )
            else:
                workout_date = self.start_date + timedelta(days=day_num - 1)

            # FIX: Extraire le nom descriptif (première ligne du contenu)
            workout_content.strip().split("\n")[0]

            # FIX: Utiliser workout_name (depuis délimiteur) comme nom principal
            # Et first_line comme description courte
            workout_display_name = workout_name.strip()

            workouts.append(
                {
                    "filename": workout_name.strip(),
                    "day": day_num,
                    "suffix": suffix,  # 'a', 'b', ou '' pour double séance
                    "date": workout_date.strftime("%Y-%m-%d"),
                    "name": workout_display_name,  # ← FIX: Utiliser le nom du délimiteur
                    "description": workout_content.strip(),
                }
            )

            suffix_display = f"/{suffix}" if suffix else ""
            print(
                f"  ✅ Jour {day_num:02d}{suffix_display} ({workout_date.strftime('%d/%m')}) : {workout_name}"
            )

        print(f"\n📊 Total : {len(workouts)} workout(s) détectés")

        # VALIDATION AUTOMATIQUE
        if workouts:
            print("\n🔍 Validation qualité notation...")
            all_warnings = []
            critical_warnings = []

            for workout in workouts:
                warnings = self.validate_workout_notation(workout)
                all_warnings.extend(warnings)
                # Séparer warnings critiques (warmup/cooldown manquants)
                critical_warnings.extend([w for w in warnings if "🚨" in w])

            if all_warnings:
                print()
                for warning in all_warnings:
                    print(f"  {warning}")
                print()

                if critical_warnings:
                    print("🚨 ERREURS CRITIQUES DÉTECTÉES - Upload BLOQUÉ")
                    print("   Des séances sont incomplètes ou mal formatées:")
                    print("   - Warmup/cooldown manquants")
                    print("   - Tirets manquants devant les instructions")
                    print("   → Utilisez format-planning pour corriger le format")
                    return []
            else:
                print("  ✅ Validation réussie - notation conforme")

        return workouts

    def parse_clipboard(self) -> list[dict]:
        """Parse les workouts depuis le presse-papier."""
        import subprocess

        print("\n📋 Lecture presse-papier...")

        try:
            result = subprocess.run(["pbpaste"], capture_output=True, text=True, check=True)
            content = result.stdout
        except Exception as e:
            print(f"❌ Erreur lecture presse-papier : {e}")
            return []

        pattern = r"=== WORKOUT (.*?) ===\n(.*?)\n=== FIN WORKOUT ==="
        matches = re.findall(pattern, content, re.DOTALL)

        # Mode single workout : utiliser date exacte
        single_workout_mode = len(matches) == 1
        if single_workout_mode:
            print("  ℹ️  Mode single workout détecté - utilisation date exacte")

        workouts = []
        for workout_name, workout_content in matches:
            day_match = re.search(r"-(\d{2})-", workout_name)
            if not day_match:
                continue

            day_num = int(day_match.group(1))

            # Si single workout, utiliser start_date directement
            if single_workout_mode:
                workout_date = self.start_date
                print(
                    f"  📌 Workout sera uploadé le {workout_date.strftime('%d/%m/%Y')} (date explicite)"
                )
            else:
                workout_date = self.start_date + timedelta(days=day_num - 1)

            # FIX: Extraire le nom descriptif (première ligne du contenu)
            workout_content.strip().split("\n")[0]

            # FIX: Utiliser workout_name (depuis délimiteur) comme nom principal
            workout_display_name = workout_name.strip()

            workouts.append(
                {
                    "filename": workout_name.strip(),
                    "day": day_num,
                    "date": workout_date.strftime("%Y-%m-%d"),
                    "name": workout_display_name,  # ← FIX: Utiliser le nom du délimiteur
                    "description": workout_content.strip(),
                }
            )

            print(f"  ✅ Jour {day_num:02d} ({workout_date.strftime('%d/%m')}) : {workout_name}")

        print(f"\n📊 Total : {len(workouts)} workout(s) dans le presse-papier")

        # VALIDATION AUTOMATIQUE
        if workouts:
            print("\n🔍 Validation qualité notation...")
            all_warnings = []
            critical_warnings = []

            for workout in workouts:
                warnings = self.validate_workout_notation(workout)
                all_warnings.extend(warnings)
                # Séparer warnings critiques (warmup/cooldown manquants)
                critical_warnings.extend([w for w in warnings if "🚨" in w])

            if all_warnings:
                print()
                for warning in all_warnings:
                    print(f"  {warning}")
                print()

                if critical_warnings:
                    print("🚨 ERREURS CRITIQUES DÉTECTÉES - Upload BLOQUÉ")
                    print("   Des séances sont incomplètes ou mal formatées:")
                    print("   - Warmup/cooldown manquants")
                    print("   - Tirets manquants devant les instructions")
                    print("   → Utilisez format-planning pour corriger le format")
                    return []
            else:
                print("  ✅ Validation réussie - notation conforme")

        return workouts
