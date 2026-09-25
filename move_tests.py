import os
import shutil

def rename_tests():
    for src_dir, dst_dir in [
        ('tests/phase1_scout_pipeline', 'tests/phase1_scout/'),
        ('tests/phase2_synthesis_gemeinde', 'tests/phase2_synthesis/')
    ]:
        for item in os.listdir(src_dir):
            src_path = os.path.join(src_dir, item)
            if os.path.isfile(src_path):
                shutil.copy(src_path, dst_dir)

    publicai_tests = ['test_crawler.py', 'test_config.py', 'test_contracts.py']
    for item in publicai_tests:
        src = os.path.join('tests/alternative_pipeline_publicai', item)
        if os.path.exists(src):
            shutil.copy(src, 'tests/phase1_scout/test_publicai_' + item.replace('test_', ''))

rename_tests()
