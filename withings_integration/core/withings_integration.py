"""
Module d'intégration Withings pour le suivi d'entraînement
Récupération des données de sommeil et de poids
"""

import json
import os
from datetime import datetime, timedelta

from withings_api import AuthScope, WithingsApi, WithingsAuth
from withings_api.common import MeasureType, SleepGetSummaryField


class WithingsIntegration:
    """Gestion de l'intégration Withings pour données sommeil et poids"""

    def __init__(self, client_id: str, client_secret: str, callback_uri: str):
        """
        Initialise l'intégration Withings

        Args:
            client_id: ClientID Withings (depuis Developer Dashboard)
            client_secret: Secret Withings
            callback_uri: URL de callback OAuth
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.callback_uri = callback_uri
        self.credentials = None
        self.api = None

    def get_authorization_url(self) -> str:
        """
        Génère l'URL d'autorisation pour OAuth2

        Returns:
            URL à ouvrir dans le navigateur pour autoriser l'application
        """
        auth = WithingsAuth(
            client_id=self.client_id,
            consumer_secret=self.client_secret,
            callback_uri=self.callback_uri,
            scope=(
                AuthScope.USER_METRICS,  # Pour poids
                AuthScope.USER_ACTIVITY,  # Pour sommeil
            ),
        )

        authorize_url = auth.get_authorize_url()
        print("\nOuvrez cette URL dans votre navigateur:")
        print(f"{authorize_url}\n")

        return authorize_url

    def authenticate_with_code(self, authorization_code: str) -> dict:
        """
        Complète l'authentification avec le code reçu du callback

        Args:
            authorization_code: Code reçu après autorisation

        Returns:
            Credentials dict pour sauvegarde
        """
        auth = WithingsAuth(
            client_id=self.client_id,
            consumer_secret=self.client_secret,
            callback_uri=self.callback_uri,
        )

        self.credentials = auth.get_credentials(authorization_code)
        self.api = WithingsApi(self.credentials)

        return {
            "access_token": self.credentials.access_token,
            "refresh_token": self.credentials.refresh_token,
            "token_expiry": self.credentials.token_expiry,
            "token_type": self.credentials.token_type,
            "userid": self.credentials.userid,
        }

    def load_credentials(self, credentials_dict: dict):
        """
        Charge des credentials sauvegardés

        Args:
            credentials_dict: Dictionnaire avec tokens
        """
        from withings_api.common import Credentials2

        self.credentials = Credentials2(
            access_token=credentials_dict["access_token"],
            refresh_token=credentials_dict["refresh_token"],
            token_expiry=credentials_dict["token_expiry"],
            token_type=credentials_dict["token_type"],
            userid=credentials_dict["userid"],
            client_id=self.client_id,
            consumer_secret=self.client_secret,
        )

        self.api = WithingsApi(self.credentials, refresh_cb=self._refresh_callback)

    def _refresh_callback(self, credentials):
        """Callback appelé lors du refresh du token"""
        self.credentials = credentials
        print("Token Withings rafraîchi automatiquement")

    def get_weight_data(self, start_date: datetime, end_date: datetime) -> list[dict]:
        """
        Récupère les données de poids sur une période

        Args:
            start_date: Date de début
            end_date: Date de fin

        Returns:
            Liste des mesures de poids avec dates
        """
        if not self.api:
            raise ValueError("API non initialisée. Authentifiez-vous d'abord.")

        measures = self.api.measure_get_meas(
            startdate=start_date, enddate=end_date, meastype=MeasureType.WEIGHT
        )

        weight_data = []
        for measure_group in measures.measuregrps:
            date = measure_group.date

            for measure in measure_group.measures:
                if measure.type == MeasureType.WEIGHT:
                    # Convertir la valeur (unit = puissance de 10)
                    weight_kg = measure.value * (10**measure.unit)

                    weight_data.append(
                        {
                            "date": date.strftime("%Y-%m-%d"),
                            "datetime": date.isoformat(),
                            "weight_kg": round(weight_kg, 1),
                            "timestamp": int(date.timestamp()),
                        }
                    )

        # Trier par date
        weight_data.sort(key=lambda x: x["timestamp"])
        return weight_data

    def get_latest_weight(self) -> dict | None:
        """
        Récupère la dernière mesure de poids

        Returns:
            Dictionnaire avec la dernière mesure ou None
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)  # Chercher sur 7 derniers jours

        weight_data = self.get_weight_data(start_date, end_date)

        return weight_data[-1] if weight_data else None

    def get_sleep_data(self, start_date: datetime, end_date: datetime) -> list[dict]:
        """
        Récupère les données de sommeil sur une période

        Args:
            start_date: Date de début
            end_date: Date de fin

        Returns:
            Liste des sessions de sommeil avec métriques
        """
        if not self.api:
            raise ValueError("API non initialisée. Authentifiez-vous d'abord.")

        sleep_summary = self.api.sleep_get_summary(
            startdateymd=start_date,
            enddateymd=end_date,
            data_fields=[
                SleepGetSummaryField.BREATHING_DISTURBANCES_INTENSITY,
                SleepGetSummaryField.DEEP_SLEEP_DURATION,
                SleepGetSummaryField.LIGHT_SLEEP_DURATION,
                SleepGetSummaryField.REM_SLEEP_DURATION,
                SleepGetSummaryField.SLEEP_SCORE,
                SleepGetSummaryField.TOTAL_SLEEP_TIME,
                SleepGetSummaryField.WAKEUP_DURATION,
                SleepGetSummaryField.WAKEUP_COUNT,
            ],
        )

        sleep_data = []
        for series in sleep_summary.series:
            sleep_entry = {
                "date": series.date.strftime("%Y-%m-%d"),
                "startdate": series.startdate.isoformat(),
                "enddate": series.enddate.isoformat(),
                "total_sleep_hours": round(series.data.total_sleep_time / 3600, 2)
                if series.data.total_sleep_time
                else None,
                "deep_sleep_minutes": round(series.data.deepsleepduration / 60, 1)
                if series.data.deepsleepduration
                else None,
                "light_sleep_minutes": round(series.data.lightsleepduration / 60, 1)
                if series.data.lightsleepduration
                else None,
                "rem_sleep_minutes": round(series.data.remsleepduration / 60, 1)
                if series.data.remsleepduration
                else None,
                "wakeup_count": series.data.wakeupcount if series.data.wakeupcount else 0,
                "wakeup_minutes": round(series.data.wakeupduration / 60, 1)
                if series.data.wakeupduration
                else None,
                "sleep_score": series.data.sleep_score if series.data.sleep_score else None,
                "breathing_disturbances": series.data.breathing_disturbances_intensity
                if series.data.breathing_disturbances_intensity
                else None,
            }

            sleep_data.append(sleep_entry)

        return sleep_data

    def get_last_night_sleep(self) -> dict | None:
        """
        Récupère les données de sommeil de la dernière nuit

        Returns:
            Dictionnaire avec les données de sommeil ou None
        """
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        sleep_data = self.get_sleep_data(yesterday, today)

        return sleep_data[0] if sleep_data else None

    def get_sleep_quality_assessment(self, sleep_data: dict) -> dict:
        """
        Évalue la qualité du sommeil selon les critères d'entraînement

        Args:
            sleep_data: Données de sommeil d'une nuit

        Returns:
            Assessment avec recommandations
        """
        total_hours = sleep_data.get("total_sleep_hours", 0)
        score = sleep_data.get("sleep_score", 0)
        deep_sleep = sleep_data.get("deep_sleep_minutes", 0)

        # Critères pour entraînement intensif
        quality = {
            "sufficient_duration": total_hours >= 7,
            "target_duration": total_hours,
            "sleep_score": score,
            "deep_sleep_ok": deep_sleep >= 60,  # Au moins 1h de sommeil profond
            "ready_for_vo2": False,
            "recommendations": [],
        }

        # Évaluation globale
        if total_hours < 5.5:
            quality["recommendations"].append("VETO séance intensive - sommeil insuffisant")
            quality["recommended_intensity"] = "recovery_only"
        elif total_hours < 7:
            quality["recommendations"].append("Éviter VO2 max - sommeil sous optimal")
            quality["recommended_intensity"] = "endurance_max"
        elif score and score > 75 and deep_sleep >= 60:
            quality["ready_for_vo2"] = True
            quality["recommendations"].append("Conditions optimales pour séance intensive")
            quality["recommended_intensity"] = "all_systems_go"
        else:
            quality["recommendations"].append("Sommeil correct - séances modérées OK")
            quality["recommended_intensity"] = "moderate"

        return quality


# Fonctions utilitaires pour l'intégration avec Intervals.icu
def sync_weight_to_intervals(withings_data: dict, intervals_api_key: str, athlete_id: str):
    """
    Synchronise le poids vers Intervals.icu

    Args:
        withings_data: Données de poids de Withings
        intervals_api_key: Clé API Intervals.icu
        athlete_id: ID athlète Intervals.icu
    """
    import requests

    url = f"https://intervals.icu/api/v1/athlete/{athlete_id}/wellness/{withings_data['date']}"

    headers = {"Authorization": f"Basic {intervals_api_key}", "Content-Type": "application/json"}

    data = {"weight": withings_data["weight_kg"]}

    response = requests.put(url, headers=headers, json=data)

    if response.status_code == 200:
        print(f"✓ Poids synchronisé: {withings_data['weight_kg']}kg le {withings_data['date']}")
    else:
        print(f"✗ Erreur sync poids: {response.status_code}")
        print(response.text)


def sync_sleep_to_intervals(sleep_data: dict, intervals_api_key: str, athlete_id: str):
    """
    Synchronise les données de sommeil vers Intervals.icu

    Args:
        sleep_data: Données de sommeil de Withings
        intervals_api_key: Clé API Intervals.icu
        athlete_id: ID athlète Intervals.icu
    """
    import requests

    url = f"https://intervals.icu/api/v1/athlete/{athlete_id}/wellness/{sleep_data['date']}"

    headers = {"Authorization": f"Basic {intervals_api_key}", "Content-Type": "application/json"}

    # Conversion heures → secondes pour Intervals.icu
    sleep_seconds = (
        int(sleep_data["total_sleep_hours"] * 3600) if sleep_data["total_sleep_hours"] else None
    )

    data = {
        "sleepSecs": sleep_seconds,
        "sleepQuality": sleep_data.get("sleep_score"),
        "comments": f"Sommeil profond: {sleep_data.get('deep_sleep_minutes')}min, "
        f"Réveils: {sleep_data.get('wakeup_count')}",
    }

    response = requests.put(url, headers=headers, json=data)

    if response.status_code == 200:
        print(f"✓ Sommeil synchronisé: {sleep_data['total_sleep_hours']}h le {sleep_data['date']}")
    else:
        print(f"✗ Erreur sync sommeil: {response.status_code}")
        print(response.text)


# Script d'exemple d'utilisation
if __name__ == "__main__":
    # Configuration (à adapter avec tes vraies valeurs)
    CLIENT_ID = "c5e8820a701242a8708c54ee9fcc83915f02270f2ae0930b9a5917bbb3d21278"
    CLIENT_SECRET = os.getenv("WITHINGS_SECRET")  # À définir dans .env
    CALLBACK_URI = (
        "https://4f3c-2a01-cb14-8513-df00-2031-d098-d697-75c1.ngrok-free.app/auth/withings/callback"
    )

    # Initialisation
    withings = WithingsIntegration(CLIENT_ID, CLIENT_SECRET, CALLBACK_URI)

    # Première connexion (à faire une seule fois)
    # auth_url = withings.get_authorization_url()
    # authorization_code = input("Entrez le code d'autorisation: ")
    # credentials = withings.authenticate_with_code(authorization_code)
    #
    # # Sauvegarder les credentials
    # with open('withings_credentials.json', 'w') as f:
    #     json.dump(credentials, f)

    # Connexions suivantes (charger credentials sauvegardés)
    with open("withings_credentials.json") as f:
        credentials = json.load(f)

    withings.load_credentials(credentials)

    # Récupérer dernière nuit de sommeil
    sleep = withings.get_last_night_sleep()
    if sleep:
        print("\n=== SOMMEIL DERNIÈRE NUIT ===")
        print(f"Date: {sleep['date']}")
        print(f"Durée totale: {sleep['total_sleep_hours']}h")
        print(f"Sommeil profond: {sleep['deep_sleep_minutes']}min")
        print(f"Score: {sleep['sleep_score']}/100")

        # Évaluation pour entraînement
        assessment = withings.get_sleep_quality_assessment(sleep)
        print(f"\n{'='*50}")
        print("RECOMMANDATIONS ENTRAÎNEMENT:")
        print(f"{'='*50}")
        for rec in assessment["recommendations"]:
            print(f"• {rec}")

    # Récupérer dernier poids
    weight = withings.get_latest_weight()
    if weight:
        print("\n=== POIDS RÉCENT ===")
        print(f"Date: {weight['date']}")
        print(f"Poids: {weight['weight_kg']}kg")
