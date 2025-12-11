#!/usr/bin/env python3
"""
Script d'application du patch workflow_coach.py
Corrige le bug athlete_id=None (ligne 235)

Usage:
    # Depuis la racine du projet :
    python3 apply_workflow_patch.py
    
    # Depuis scripts/ :
    python3 scripts/apply_workflow_patch.py
    
    # Ou directement depuis scripts/ :
    cd scripts && python3 apply_workflow_patch.py
"""

import sys
from pathlib import Path

def find_workflow_file():
    """Trouver workflow_coach.py automatiquement"""
    # Essayer depuis le répertoire courant
    if Path("workflow_coach.py").exists():
        return Path("workflow_coach.py")
    
    # Essayer depuis scripts/
    if Path("scripts/workflow_coach.py").exists():
        return Path("scripts/workflow_coach.py")
    
    # Essayer depuis le parent (si on est dans scripts/)
    if Path("../scripts/workflow_coach.py").exists():
        return Path("../scripts/workflow_coach.py")
    
    return None

def apply_patch():
    workflow_file = find_workflow_file()
    
    if workflow_file is None:
        print("❌ Fichier workflow_coach.py non trouvé")
        print("\n📁 Exécutez ce script depuis :")
        print("   • La racine du projet")
        print("   • Le dossier scripts/")
        return False
    
    print(f"✅ Fichier trouvé : {workflow_file}")
    
    with open(workflow_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Backup
    backup_file = workflow_file.with_suffix('.py.backup')
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print(f"✅ Backup : {backup_file}")
    
    # Insérer load_credentials avant clear_screen
    insert_line = None
    for i, line in enumerate(lines):
        if 'def clear_screen(self):' in line:
            insert_line = i
            break
    
    if insert_line is None:
        print("❌ 'def clear_screen' non trouvé")
        return False
    
    new_method = '''    def load_credentials(self):
        """Charger credentials Intervals.icu de manière robuste"""
        import os
        import json
        from pathlib import Path
        
        config_path = Path.home() / ".intervals_config.json"
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    athlete_id = config.get('athlete_id')
                    api_key = config.get('api_key')
                    if athlete_id and api_key:
                        return athlete_id, api_key
            except Exception as e:
                print(f"⚠️  Erreur config : {e}")
        
        athlete_id = os.getenv('VITE_INTERVALS_ATHLETE_ID')
        api_key = os.getenv('VITE_INTERVALS_API_KEY')
        if athlete_id and api_key:
            return athlete_id, api_key
        
        return None, None

'''
    
    lines.insert(insert_line, new_method)
    print(f"✅ load_credentials() ajoutée ligne {insert_line}")
    
    # Remplacer os.getenv par self.load_credentials()
    modified = False
    for i, line in enumerate(lines):
        if 'athlete_id=os.getenv(\'VITE_INTERVALS_ATHLETE_ID\')' in line:
            start = i
            while start > 0 and 'from prepare_analysis import IntervalsAPI' not in lines[start]:
                start -= 1
            
            end = i
            while end < len(lines) and 'activities = api.get_activities' not in lines[end]:
                end += 1
            end += 1
            
            indent = ' ' * 12
            new_block = f'''{indent}from prepare_analysis import IntervalsAPI
{indent}
{indent}# FIX: Charger credentials
{indent}athlete_id, api_key = self.load_credentials()
{indent}
{indent}if not athlete_id or not api_key:
{indent}    print()
{indent}    print("ℹ️  Credentials non trouvés")
{indent}    print("   → Feedback sans contexte")
{indent}    raise ValueError("No credentials")
{indent}
{indent}api = IntervalsAPI(athlete_id=athlete_id, api_key=api_key)
{indent}
{indent}from datetime import datetime, timedelta
{indent}oldest = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
{indent}newest = datetime.now().strftime('%Y-%m-%d')
{indent}activities = api.get_activities(oldest=oldest, newest=newest)
'''
            
            lines[start:end] = [new_block]
            print(f"✅ Bloc API corrigé (lignes {start}-{end})")
            modified = True
            break
    
    if not modified:
        print("⚠️  Bloc athlete_id=os.getenv non trouvé")
        print("   Le fichier est peut-être déjà patché ?")
    
    # Améliorer message erreur
    for i, line in enumerate(lines):
        if 'print(f"⚠️  Erreur lors de la récupération du contexte : {e}")' in line:
            indent = len(line) - len(line.lstrip())
            new_line = ' ' * indent + 'print("   → Collecte feedback sans contexte activité")\n'
            if i + 1 < len(lines) and 'sans contexte activité' not in lines[i + 1]:
                lines.insert(i + 1, new_line)
                print(f"✅ Message erreur amélioré")
            break
    
    with open(workflow_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print(f"\n✅ Patch appliqué : {workflow_file}")
    print(f"\n📋 Vérifications :")
    print(f"   git diff {workflow_file}")
    print(f"   python3 {workflow_file}")
    
    return True

if __name__ == '__main__':
    sys.exit(0 if apply_patch() else 1)
