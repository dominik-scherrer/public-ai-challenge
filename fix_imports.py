import os
import glob

def replace_in_files(directory, replacements):
    for root, _, files in os.walk(directory):
        for file in files:
            if not file.endswith('.py'): continue
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            original = content
            for old, new in replacements.items():
                content = content.replace(old, new)
            if content != original:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"Updated {filepath}")

phase1_replacements = {
    'public_ai_challenge.alternative_pipeline_publicai.config': 'public_ai_challenge.phase1_scout.config',
    'public_ai_challenge.alternative_pipeline_publicai.crawler': 'public_ai_challenge.phase1_scout.crawler',
    'public_ai_challenge.alternative_pipeline_publicai.contracts': 'public_ai_challenge.phase1_scout.publicai_contracts',
    'public_ai_challenge.phase1_scout_pipeline.': 'public_ai_challenge.phase1_scout.',
    'from .contracts': 'from .contracts' # avoid touching this if not needed
}

phase2_replacements = {
    'public_ai_challenge.phase2_synthesis_gemeinde.': 'public_ai_challenge.phase2_synthesis.'
}

demo_replacements = {
    'public_ai_challenge.phase2_synthesis_gemeinde.adapter': 'public_ai_challenge.phase2_synthesis.adapter',
    'public_ai_challenge.phase1_scout_pipeline.adapter': 'public_ai_challenge.phase1_scout.adapter'
}

replace_in_files('src/public_ai_challenge/phase1_scout', phase1_replacements)
replace_in_files('src/public_ai_challenge/phase2_synthesis', phase2_replacements)
replace_in_files('demo', demo_replacements)
replace_in_files('tests', demo_replacements)
