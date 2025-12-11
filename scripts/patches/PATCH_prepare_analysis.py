#!/usr/bin/env python3
"""
PATCH pour prepare_analysis.py - Détection Source Améliorée

Ce patch améliore la fonction de détection des activités avec données limitées
pour éviter les faux positifs et améliorer la clarté des messages.

Usage:
    1. Sauvegarder l'ancien prepare_analysis.py
    2. Appliquer ce patch aux lignes concernées
    3. Tester avec activités Zwift et Strava
"""

# ==============================================================================
# FONCTION AMÉLIORÉE - À AJOUTER AVANT format_activity_data (ligne ~240)
# ==============================================================================

def is_limited_data_source(activity):
    """
    Détecter si l'activité provient d'une source avec données API limitées
    
    Args:
        activity: Dict contenant les données de l'activité
        
    Returns:
        tuple: (is_limited: bool, reason: str, recommendations: list)
        
    Exemples:
        >>> activity_strava = {'source': 'STRAVA', 'icu_average_watts': 0}
        >>> is_limited, reason, reco = is_limited_data_source(activity_strava)
        >>> is_limited
        True
        >>> reason
        'Source Strava avec restrictions API'
    """
    source = activity.get('source', 'Unknown')
    avg_power = activity.get('icu_average_watts', 0)
    avg_hr = activity.get('average_heartrate', 0)
    
    # CAS 1: Activité Strava (restrictions API connues)
    if source == 'STRAVA':
        return (
            True,
            'Source Strava avec restrictions API',
            [
                'Vérifier les métriques sur Intervals.icu web',
                'Les données de puissance peuvent être manquantes',
                'Utiliser les données disponibles pour analyse qualitative'
            ]
        )
    
    # CAS 2: Activité uploadée mais sans capteur de puissance
    if source in ['UPLOAD', 'FILE_UPLOAD'] and avg_power == 0:
        if avg_hr > 0:
            return (
                False,  # Pas limité, juste pas de capteur puissance
                'Séance sans capteur de puissance (FC disponible)',
                [
                    'Analyse basée sur fréquence cardiaque',
                    'RPE et ressenti subjectif importants',
                    'Considérer ajout capteur de puissance'
                ]
            )
        else:
            return (
                True,
                'Données physiologiques manquantes',
                [
                    'Séance sans capteur de puissance ni FC',
                    'Analyse limitée aux métriques basiques',
                    'Utiliser RPE et ressenti pour compléter'
                ]
            )
    
    # CAS 3: Activité manuelle (MANUAL)
    if source == 'MANUAL':
        return (
            False,  # Pas limité, données saisies manuellement
            'Séance saisie manuellement',
            [
                'Données saisies par l\'athlète',
                'Vérifier cohérence avec séances similaires',
                'Encourager utilisation fichiers .fit si possible'
            ]
        )
    
    # CAS 4: Données complètes (UPLOAD avec capteurs)
    if source in ['UPLOAD', 'FILE_UPLOAD'] and avg_power > 0:
        return (
            False,
            'Données complètes disponibles',
            []
        )
    
    # CAS 5: Source inconnue
    return (
        True,
        f'Source inconnue: {source}',
        ['Vérifier l\'origine de l\'activité sur Intervals.icu']
    )


def format_limited_data_warning(is_limited, reason, recommendations):
    """
    Formater un message de warning pour données limitées
    
    Args:
        is_limited: bool - True si données limitées
        reason: str - Raison de la limitation
        recommendations: list - Liste de recommandations
        
    Returns:
        str: Message formaté ou chaîne vide
    """
    if not is_limited:
        return ""
    
    lines = [
        "",
        "⚠️  ATTENTION : Données limitées",
        f"   Raison : {reason}",
        ""
    ]
    
    if recommendations:
        lines.append("   Recommandations :")
        for reco in recommendations:
            lines.append(f"   • {reco}")
        lines.append("")
    
    return "\n".join(lines)


# ==============================================================================
# MODIFICATION format_activity_data - REMPLACER LIGNES 241-268
# ==============================================================================

def format_activity_data_NOUVEAU(self, activity):
    """
    Formater les données d'activité pour le prompt
    VERSION AMÉLIORÉE avec détection source robuste
    """
    date = datetime.fromisoformat(activity['start_date_local'].replace('Z', '+00:00'))
    
    # Nouvelle détection avec analyse détaillée
    is_limited, reason, recommendations = is_limited_data_source(activity)
    
    data = {
        'name': activity.get('name', 'Séance'),
        'type': activity.get('type', 'Cyclisme'),
        'date': date.strftime('%d/%m/%Y'),
        'date_iso': date.strftime('%Y-%m-%d'),
        'duration_min': activity.get('moving_time', 0) // 60,
        'tss': activity.get('icu_training_load', 0),
        'intensity': activity.get('icu_intensity', 0) / 100.0,
        'avg_power': activity.get('icu_average_watts', 0),
        'np': activity.get('icu_weighted_avg_watts', 0),
        'avg_cadence': activity.get('average_cadence', 0),
        'avg_hr': activity.get('average_heartrate', 0),
        'max_hr': activity.get('max_heartrate', 0),
        'decoupling': activity.get('decoupling', None),
        'description': activity.get('description', ''),
        'tags': activity.get('tags', []),
        
        # Nouveaux champs pour gestion améliorée
        'source': activity.get('source', 'Unknown'),
        'is_limited_data': is_limited,
        'data_limitation_reason': reason if is_limited else None,
        'data_recommendations': recommendations if is_limited else [],
        
        # Ancien champ pour compatibilité
        'is_strava': activity.get('source') == 'STRAVA',
    }
    
    return data


# ==============================================================================
# MODIFICATION main() - REMPLACER LIGNES 1068-1075
# ==============================================================================

def main_PATCH_warning_display():
    """
    Patch pour l'affichage du warning dans la fonction main()
    Remplacer les lignes 1068-1075
    """
    # Vérifier les limitations de données (remplace le test Strava simple)
    is_limited, reason, recommendations = is_limited_data_source(activity)
    
    if is_limited:
        warning_message = format_limited_data_warning(is_limited, reason, recommendations)
        print(warning_message)
    else:
        print("   ✅ Données complètes disponibles")
    
    print()


# ==============================================================================
# INSTRUCTIONS D'APPLICATION
# ==============================================================================

PATCH_INSTRUCTIONS = """
INSTRUCTIONS POUR APPLIQUER LE PATCH
====================================

1. SAUVEGARDE
   cd ~/cyclisme-training-logs/scripts
   cp prepare_analysis.py prepare_analysis.py.backup.$(date +%Y%m%d)

2. AJOUT DES NOUVELLES FONCTIONS (avant ligne 240)
   - Copier is_limited_data_source()
   - Copier format_limited_data_warning()

3. REMPLACEMENT format_activity_data (lignes 241-268)
   - Remplacer par format_activity_data_NOUVEAU()
   - Attention : Garder la déclaration de classe/self

4. REMPLACEMENT WARNING (lignes 1068-1075)
   - Remplacer le bloc if source == 'STRAVA'
   - Par le code de main_PATCH_warning_display()

5. TEST VALIDATION
   cd ~/cyclisme-training-logs
   
   # Test 1 : Activité Zwift (UPLOAD avec données)
   python3 scripts/prepare_analysis.py --activity-id i107093941
   # Attendu: "✅ Données complètes disponibles"
   
   # Test 2 : Activité Strava (données limitées)
   python3 scripts/prepare_analysis.py --activity-id 16457456654
   # Attendu: "⚠️ ATTENTION : Données limitées"
   
6. COMMIT SI OK
   git add scripts/prepare_analysis.py
   git commit -m "fix: Amélioration détection source activités"
   git push

ROLLBACK SI PROBLÈME
   cp prepare_analysis.py.backup.YYYYMMDD prepare_analysis.py

AIDE
   Si questions ou erreurs, consulter DIAGNOSTIC_COMPLET.md
"""

if __name__ == '__main__':
    print(PATCH_INSTRUCTIONS)
