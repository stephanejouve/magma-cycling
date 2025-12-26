#!/usr/bin/env python3
"""
Legacy statistics computation (use analyzers/weekly_analyzer.py for new code).

GARTNER_TIME: T
STATUS: Production (Legacy)
LAST_REVIEW: 2025-12-26
PRIORITY: P3
REPLACEMENT: analyzers/weekly_analyzer.py (Planned Phase 2)
DEPRECATION_PLAN: Replace after Prompt 2 Phase 2 (weekly analysis system)
DOCSTRING: v2

⚠️  LEGACY - Calculs statistiques basiques workouts. Utilisé temporairement
en attendant weekly_analyzer.py (Prompt 2 Phase 2). Pour nouveau code,
utiliser analyzers/weekly_analyzer.py.

Examples:
    Basic stats (legacy)::

        from cyclisme_training_logs.stats import compute_weekly_stats

        # ⚠️  Legacy - à remplacer
        stats = compute_weekly_stats(
            week="S073",
            activities=[...]
        )

        print(f"Total TSS: {stats['total_tss']}")

    Migration to new system::

        # ✅ NOUVEAU (Phase 2) - À utiliser pour nouveau code
        from cyclisme_training_logs.analyzers.weekly_analyzer import WeeklyAnalyzer

        analyzer = WeeklyAnalyzer(week="S073")
        analysis = analyzer.analyze()

        # 6 reports générés automatiquement
        print(analysis['reports'])

    CLI (legacy)::

        # ⚠️  Legacy command
        poetry run stats --week S073

        # ✅ NOUVEAU (Phase 2)
        poetry run weekly-analysis --week S073

Author: Stéphane Jouve
Created: 2024-08-XX
Updated: 2025-12-26 (Standardization Prompt 3 Priority 2 - Marked as Legacy)
"""

import re
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

def extract_tss_from_workouts(file_path):
    """Extrait les TSS depuis workouts-history.md"""
    if not file_path.exists():
        return []
    
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Regex pour extraire TSS et dates
    # Format attendu: "TSS : XX" ou "TSS: XX"
    pattern = r'Date\s*:\s*(\d{2}/\d{2}/\d{4}).*?TSS\s*:\s*(\d+)'
    matches = re.findall(pattern, content, re.DOTALL)
    
    for date_str, tss in matches:
        try:
            date = datetime.strptime(date_str, '%d/%m/%Y')
            data.append({'date': date, 'tss': int(tss)})
        except ValueError:
            continue
    
    return data

def calculate_weekly_tss(sessions):
    """Calcule TSS par semaine"""
    weekly = defaultdict(int)
    for session in sessions:
        # Numéro de semaine ISO
        week = session['date'].isocalendar()[1]
        year = session['date'].year
        key = f"{year}-W{week:02d}"
        weekly[key] += session['tss']
    
    return dict(sorted(weekly.items()))

def extract_ftp_evolution(file_path):
    """Extrait l'évolution FTP depuis metrics-evolution.md"""
    if not file_path.exists():
        return []
    
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Chercher le tableau FTP
    # Format: | JJ/MM/AAAA | XXX | X.XX | Contexte |
    in_table = False
    for line in content.split('\n'):
        if '| Date | Valeur (W) | W/kg | Contexte |' in line:
            in_table = True
            continue
        if in_table and line.startswith('|'):
            parts = [p.strip() for p in line.split('|')[1:-1]]
            if len(parts) >= 3 and parts[0] and parts[0] != '---':
                try:
                    date = datetime.strptime(parts[0], '%d/%m/%Y')
                    ftp = int(parts[1])
                    wkg = float(parts[2])
                    data.append({'date': date, 'ftp': ftp, 'wkg': wkg})
                except (ValueError, IndexError):
                    continue
    
    return data

def main():
    # Use data repo config if available
    from cyclisme_training_logs.config import get_data_config
    try:
        config = get_data_config()
        workouts_file = config.workouts_history_path
        metrics_file = config.data_repo_path / 'metrics-evolution.md'
    except FileNotFoundError:
        # Fallback to legacy paths
        root = Path(__file__).parent.parent
        workouts_file = root / 'logs' / 'workouts-history.md'
        metrics_file = root / 'logs' / 'metrics-evolution.md'
    
    print("📊 Statistiques d'Entraînement")
    print("=" * 50)
    
    # TSS par semaine
    print("\n🏋️  TSS Hebdomadaire:")
    sessions = extract_tss_from_workouts(workouts_file)
    if sessions:
        weekly_tss = calculate_weekly_tss(sessions)
        for week, tss in list(weekly_tss.items())[-8:]:  # 8 dernières semaines
            print(f"  {week}: {tss:>4} TSS")
        
        total_tss = sum(session['tss'] for session in sessions)
        avg_tss = total_tss / len(sessions) if sessions else 0
        print(f"\n  Total séances: {len(sessions)}")
        print(f"  TSS total: {total_tss}")
        print(f"  TSS moyen/séance: {avg_tss:.1f}")
    else:
        print("  Aucune donnée disponible")
    
    # Évolution FTP
    print("\n📈 Évolution FTP:")
    ftp_data = extract_ftp_evolution(metrics_file)
    if ftp_data:
        for entry in ftp_data:
            date_str = entry['date'].strftime('%d/%m/%Y')
            print(f"  {date_str}: {entry['ftp']:>3}W ({entry['wkg']:.2f} W/kg)")
        
        if len(ftp_data) > 1:
            first = ftp_data[0]
            last = ftp_data[-1]
            delta = last['ftp'] - first['ftp']
            delta_pct = (delta / first['ftp']) * 100
            print(f"\n  Progression: {delta:+d}W ({delta_pct:+.1f}%)")
    else:
        print("  Aucune donnée disponible")
    
    print("\n" + "=" * 50)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrompu par l'utilisateur")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erreur: {e}", file=sys.stderr)
        sys.exit(1)
