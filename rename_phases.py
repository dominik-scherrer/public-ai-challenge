import os
import shutil

replacements = {
    'phase1_scout': 'phase1_scout',
    'phase2_synthesis': 'phase2_synthesis',
    'phase3_judge': 'phase3_judge',
    'phase4_mcp': 'phase4_mcp'
}

# 1. Rename directories
for base_dir in ['src/public_ai_challenge', 'tests']:
    if not os.path.exists(base_dir): continue
    for old, new in replacements.items():
        old_path = os.path.join(base_dir, old)
        new_path = os.path.join(base_dir, new)
        if os.path.exists(old_path):
            os.rename(old_path, new_path)

# 2. Update imports in all files
for root, _, files in os.walk('.'):
    if '.venv' in root or '.git' in root or '__pycache__' in root:
        continue
    for file in files:
        if not file.endswith(('.py', '.md')): continue
        filepath = os.path.join(root, file)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except:
            continue
            
        original = content
        for old, new in replacements.items():
            content = content.replace(old, new)
            
        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Updated {filepath}")
