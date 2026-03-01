"""Metric extraction and formatting helpers for PromptGenerator."""


class MetricHelpersMixin:
    """Unit-level metric extraction and formatting."""

    def _format_feel_value(self, feel_value):
        """Format the 'feel' value (Intervals.icu 1-5 scale) into readable text.

        Args:
            feel_value: Numeric value 1-5 or None (1=Excellent, 5=Poor)

        Returns:
            Formatted string with emoji
        """
        if feel_value is None:
            return "_Non renseigné_"

        feel_map = {
            1: "😊 Excellent (1/5)",
            2: "🙂 Bien (2/5)",
            3: "😐 Moyen (3/5)",
            4: "😕 Passable (4/5)",
            5: "😣 Mauvais (5/5)",
        }

        return feel_map.get(feel_value, f"_Valeur inconnue: {feel_value}_")

    def _format_athlete_notes(self, activity_description, wellness_comments):
        """Format athlete notes with wellness comments as fallback.

        Args:
            activity_description: Notes from activity description field
            wellness_comments: Notes from wellness comments field

        Returns:
            Formatted string with notes and source indication
        """
        # Priority 1: Activity description
        if activity_description and activity_description.strip():
            return activity_description.strip()

        # Priority 2: Wellness comments (fallback)
        if wellness_comments and wellness_comments.strip():
            return f"{wellness_comments.strip()}\n\n_Note: Feedback saisi dans wellness (pas de description activité)_"

        # No notes at all
        return "_Aucune note saisie_"

    def _format_temperature_data(self, avg_temp, min_temp, max_temp, has_weather):
        """Format temperature data for activity analysis.

        Args:
            avg_temp: Average temperature in °C
            min_temp: Minimum temperature in °C
            max_temp: Maximum temperature in °C
            has_weather: Whether weather data is available

        Returns:
            Formatted string with temperature information
        """
        if not has_weather or avg_temp is None:
            return "_Données météo non disponibles_"

        # Format average temperature
        avg_str = f"{avg_temp:.1f}°C"

        # Add min/max if available
        if min_temp is not None and max_temp is not None:
            range_str = f" (min {min_temp}°C, max {max_temp}°C)"
        else:
            range_str = ""

        # Add contextual emoji based on temperature
        if avg_temp < 5:
            emoji = "🥶"
            context = "très froid"
        elif avg_temp < 10:
            emoji = "❄️"
            context = "froid"
        elif avg_temp < 15:
            emoji = "🌡️"
            context = "frais"
        elif avg_temp < 20:
            emoji = "☀️"
            context = "tempéré"
        elif avg_temp < 25:
            emoji = "🌤️"
            context = "agréable"
        elif avg_temp < 30:
            emoji = "☀️"
            context = "chaud"
        else:
            emoji = "🔥"
            context = "très chaud"

        return f"{emoji} {avg_str}{range_str} ({context})"

    def _format_power(self, power_dict):
        """Format une valeur de puissance (gère %, watts absolus, rampes)."""
        if not power_dict:
            return "N/A"

        units = power_dict.get("units", "")

        if units == "%ftp":
            if "value" in power_dict:
                return f"{power_dict['value']}%FTP"
            elif "start" in power_dict and "end" in power_dict:
                return f"{power_dict['start']}-{power_dict['end']}%FTP"
        elif units == "w":
            return f"{power_dict.get('value', 0)}W"
        elif units == "power_zone":
            return f"Z{power_dict.get('value', '?')}"

        return "N/A"

    def safe_format_metric(self, value, format_spec=".0f", suffix="", default="N/A"):
        """Formatage sécurisé d'une métrique pouvant être None.

        Args:
            value: Valeur à formater (peut être None)
            format_spec: Spécification de format (ex: '.0f', '.2f')
            suffix: Suffixe à ajouter (ex: 'W', 'bpm')
            default: Valeur par défaut si None

        Returns:
            str: Valeur formatée ou default.
        """
        if value is None:
            return default
        try:
            return f"{value:{format_spec}}{suffix}"
        except (ValueError, TypeError):
            return default

    def get_power_value(self, activity, metric_type="avg"):
        """Extract robuste de la puissance avec fallback multi-champs.

        Args:
            activity: Dictionnaire activité depuis API
            metric_type: 'avg' (moyenne) ou 'np' (normalisée)

        Returns:
            float ou None: Valeur de puissance trouvée.
        """
        field_mappings = {
            "avg": ["avg_power", "power", "average_power", "watts", "avgWatts"],
            "np": ["np", "normalized_power", "norm_power", "normalizedPower"],
        }

        possible_fields = field_mappings.get(metric_type, [])

        for field in possible_fields:
            value = activity.get(field)
            if value is not None and value > 0:
                return value

        return None

    def get_cadence_value(self, activity, metric_type="avg"):
        """Extract robuste de la cadence avec fallback."""
        field_mappings = {
            "avg": ["avg_cadence", "cadence", "avgCadence", "rpm"],
            "max": ["max_cadence", "maxCadence", "maximum_cadence"],
        }

        possible_fields = field_mappings.get(metric_type, [])

        for field in possible_fields:
            value = activity.get(field)
            if value is not None and value > 0:
                return value

        return None

    def get_hr_value(self, activity, metric_type="avg"):
        """Extract robuste de la fréquence cardiaque avec fallback."""
        field_mappings = {
            "avg": ["avg_hr", "hr", "avgHr", "heart_rate", "average_hr"],
            "max": ["max_hr", "maxHr", "max_heart_rate", "maximum_hr"],
        }

        possible_fields = field_mappings.get(metric_type, [])

        for field in possible_fields:
            value = activity.get(field)
            if value is not None and value > 0:
                return value

        return None
