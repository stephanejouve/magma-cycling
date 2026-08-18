"""BT-050 : distribution d'intensité par zone puissance via streams temps-réel.

Remplace le comptage historique d'activités par IF global (`sum(1 for a
if 0.85 <= a.icu_intensity < 0.95)`) qui était **faux et trompeur** :
une course de 4h à IF 0.75 n'est pas 4h en zone 3 — c'est un mix Z1-Z5
dont l'IF moyen tombe à 0.75. Une semaine avec 5 activités toutes IF ≥ 0.95
donnait « z5=5, zéro ailleurs » suggérant une polarisation extrême
inexistante.

Le nouveau calcul :

- Fetch les streams `watts` de chaque activité (endpoint Intervals.icu
  `/activity/{id}/streams`).
- Résout la FTP en vigueur à la date de l'activité (paliers historiques —
  interdit d'utiliser la FTP courante sur des activités passées, faussé).
- Bucketise chaque seconde de puissance par zone Z1-Z5 selon les bornes
  Coggan 5-zone simplifié.
- Somme sur toutes les activités de la fenêtre → temps par zone en
  secondes + pourcentage du total.

Coût réseau : 1 requête `get_activity_streams(id)` par activité (cache
read-through local BT-025 amortit sur les re-runs). Pour une fenêtre 30
jours ≈ 20-30 requêtes. Assumé — Coach AI 2026-08-17 : « à faire
correctement plutôt que vite ».

Précision Coach AI :
- FTP historique par date d'activité (pas FTP courante) — piège partagé
  avec DE-001 (filtre efficience). Cf memory
  ``reference_ftp_paliers_historique.md``.
- Restituer minutes ET pourcentage (le pct seul masque le volume ; sur
  semaines de charge très différentes, 60 % Z2 ne veut pas dire la même
  chose).
"""

from __future__ import annotations

from typing import Any

#: BT-050 : paliers FTP historique — source de vérité versionnée pour
#: toute agrégation par zones puissance rétrospective. Convention lookup :
#: pour une activité du jour ``D``, la FTP en vigueur est la valeur du
#: palier le plus récent avec date ≤ ``D``.
#:
#: Réserves qualité :
#:
#: - Palier initial 223W (2025-08-23) : établi en S080, antérieur inconnu.
#:   Pour data pré-S080 (2025-08-23 → S080 courant novembre 2025), ce
#:   palier est **supposé**, non confirmé. Rendu doit signaler la portion
#:   comme « FTP palier initial supposé ».
#: - Palier 226W (2026-03-28) : test S086-06b ``ZwiftFTPTestStandard``,
#:   partiellement dégradé (trous de puissance ROAM/Zwift désync durant
#:   le bloc test). Valeur à surveiller si écart apparaît à l'usage.
FTP_PALIERS: list[tuple[str, int]] = [
    ("2025-08-23", 223),
    ("2026-03-28", 226),
]

#: Bornes zones puissance en fraction de FTP (Coggan 5-zone simplifié,
#: aligné sur le comptage historique qui utilisait déjà ces bornes IF).
#: Intervalles ``[lo, hi)`` — la borne haute est exclusive sauf Z5 qui
#: absorbe tout ce qui dépasse 0.95 (VO2 max + neuromusculaire agrégés).
ZONE_BOUNDS: dict[str, tuple[float, float]] = {
    "z1": (0.00, 0.55),
    "z2": (0.55, 0.75),
    "z3": (0.75, 0.85),
    "z4": (0.85, 0.95),
    "z5": (0.95, float("inf")),
}


def ftp_at(activity_date: str) -> int:
    """Retourne la FTP en vigueur à ``activity_date`` (format ``YYYY-MM-DD``).

    Convention : palier le plus récent avec date ≤ ``activity_date``.
    Si ``activity_date`` est antérieure au premier palier connu, retourne
    le premier palier avec réserve documentée (rendu doit signaler).

    Args:
        activity_date: date de l'activité en ISO ``YYYY-MM-DD``.

    Returns:
        FTP entier en watts.

    Example:
        >>> ftp_at("2026-05-01")
        226
        >>> ftp_at("2025-11-15")
        223
    """
    for palier_date, ftp in reversed(FTP_PALIERS):
        if activity_date >= palier_date:
            return ftp
    # Antérieur au 1er palier connu — retour du 1er palier avec la
    # réserve documentée en top-of-module.
    return FTP_PALIERS[0][1]


def bucket_watts_by_zones(watts: list[int | float | None], ftp: int) -> dict[str, int]:
    """Bucketise chaque seconde de puissance par zone Z1-Z5.

    ``None`` traité comme 0 (pause, pas de pédalage, capteur perdu).
    Chaque seconde compte pour 1 dans exactement une zone (les bornes
    sont disjointes, Z5 absorbe l'infini).

    Args:
        watts: liste des watts par seconde (typiquement le stream
            ``type=watts`` retourné par ``client.get_activity_streams``).
        ftp: FTP en vigueur (W) pour convertir les bornes fraction → W absolus.

    Returns:
        Dict ``{zone_name: seconds_count}`` avec keys ``z1``..``z5``.
        Somme des valeurs = ``len(watts)`` (invariant).
    """
    counts: dict[str, int] = {z: 0 for z in ZONE_BOUNDS}
    if ftp <= 0:
        # Défensif : sans FTP valide, pas de bucketing possible. Retourne
        # tout en Z1 (fallback conservateur, minimise le signal parasite).
        counts["z1"] = len(watts)
        return counts
    for w in watts:
        w_val = float(w) if w is not None else 0.0
        pct = w_val / ftp
        for z, (lo, hi) in ZONE_BOUNDS.items():
            if lo <= pct < hi:
                counts[z] += 1
                break
    return counts


def intensity_distribution_from_activities(
    activities: list[dict[str, Any]],
    client: Any,
) -> dict[str, Any]:
    """Agrège la distribution d'intensité en temps par zone sur N activités.

    Fetch les streams ``watts`` de chaque activité, bucketise selon la
    FTP historique à la date de l'activité, somme sur toutes les activités.

    Args:
        activities: liste des activités Intervals (dicts avec ``id`` et
            ``start_date_local`` au minimum).
        client: instance de ``IntervalsClient`` (a la méthode
            ``get_activity_streams``).

    Returns:
        Dict avec :

        - ``z1_seconds``..``z5_seconds`` (int) : cumul secondes par zone
        - ``z1_pct``..``z5_pct`` (float, arrondi 0.1 %) : part du total
        - ``total_seconds`` (int) : total accumulé sur toutes les activités
        - ``zone_bounds`` (dict, BT-050 v2) : bornes utilisées ``{z1: [0.00, 0.55], ...}``
          exposées pour permettre la **vérification indépendante** du calcul.
        - ``ftp_by_activity`` (dict, BT-050 v2) : ``{activity_id: ftp_watts}``
          par activité **utilisée** (activités skippées absentes). Permet à
          l'IA/opérateur de vérifier que la FTP historique a bien été
          appliquée par date, pas la FTP courante.
        - ``activities_considered`` (int, BT-059) : nombre d'activités reçues
          en input (== ``len(activities)``). Sert de dénominateur pour
          interpréter ``skipped_activities`` sans consulter l'input du caller.
        - ``skipped_activities`` (list, BT-059) : activités skippées avec
          raison, chaque entrée ``{id, date, reason, error?}``. Raisons :

          * ``invalid_metadata`` : id ou date manquante côté activité
          * ``fetch_failed`` : exception au fetch (avec ``error`` tronqué à 200 chars)
          * ``no_watts_stream`` : streams récupérés mais aucun type ``watts``
          * ``empty_watts_data`` : stream watts présent mais ``data`` vide

          **Motif** : distinguer « aucun temps réalisé » (skipped vide,
          total_seconds=0) de « toutes activités échouées au fetch »
          (skipped=N tous fetch_failed, total_seconds=0). Ambiguïté signalée
          par Admin sur S106 preprod (cache miss silencieux post-backfill
          BT-025). Doctrine « P3 absence explicite » DE-002.
    """
    aggregated: dict[str, int] = {z: 0 for z in ZONE_BOUNDS}
    # BT-050 v2 : trace la FTP appliquée par activité pour audit indépendant.
    ftp_by_activity: dict[str, int] = {}
    # BT-059 : trace les activités skippées avec raison pour distinguer
    # « aucun temps réel » de « fetch failed silencieux ».
    skipped_activities: list[dict[str, Any]] = []

    for act in activities:
        activity_id = act.get("id")
        activity_date_full = act.get("start_date_local") or ""
        activity_date = activity_date_full[:10]  # YYYY-MM-DD
        if not activity_id or not activity_date:
            skipped_activities.append(
                {
                    "id": str(activity_id) if activity_id is not None else None,
                    "date": activity_date or None,
                    "reason": "invalid_metadata",
                }
            )
            continue

        try:
            streams = client.get_activity_streams(activity_id)
        except Exception as exc:
            # Une activité qui échoue au fetch (429, 5xx, timeout, cache
            # miss) est skippée — l'agrégat reste calculable sur les autres.
            # BT-059 : au lieu du skip silencieux, remonter la raison au
            # consommateur pour que « total_seconds=0 » soit interprétable
            # (« vraiment 0 » vs « tout a fail »). Error tronqué à 200 chars
            # pour éviter les leaks de bodies HTTP.
            error_msg = f"{type(exc).__name__}: {str(exc)[:200]}"
            skipped_activities.append(
                {
                    "id": str(activity_id),
                    "date": activity_date,
                    "reason": "fetch_failed",
                    "error": error_msg,
                }
            )
            continue

        watts_stream = next(
            (s for s in streams if s.get("type") == "watts"),
            None,
        )
        if not watts_stream:
            skipped_activities.append(
                {
                    "id": str(activity_id),
                    "date": activity_date,
                    "reason": "no_watts_stream",
                }
            )
            continue
        if not watts_stream.get("data"):
            skipped_activities.append(
                {
                    "id": str(activity_id),
                    "date": activity_date,
                    "reason": "empty_watts_data",
                }
            )
            continue

        ftp = ftp_at(activity_date)
        ftp_by_activity[str(activity_id)] = ftp
        counts = bucket_watts_by_zones(watts_stream["data"], ftp)
        for z, sec in counts.items():
            aggregated[z] += sec

    total = sum(aggregated.values())
    result: dict[str, Any] = {}
    for z in ZONE_BOUNDS:
        sec = aggregated[z]
        result[f"{z}_seconds"] = sec
        result[f"{z}_pct"] = round(sec / total * 100, 1) if total > 0 else 0.0
    result["total_seconds"] = total
    # BT-050 v2 : exposer les bornes utilisées + FTP appliquée par activité
    # pour permettre la vérification indépendante du calcul par l'IA ou
    # l'opérateur.
    result["zone_bounds"] = {
        z: [lo, hi if hi != float("inf") else None] for z, (lo, hi) in ZONE_BOUNDS.items()
    }
    result["ftp_by_activity"] = ftp_by_activity
    # BT-059 : compteurs de diagnostic pour interpréter total_seconds=0
    result["activities_considered"] = len(activities)
    result["skipped_activities"] = skipped_activities
    return result
