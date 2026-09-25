with open('pytest_errors2.log', 'r', encoding='utf-16') as f:
    lines = f.readlines()
for line in lines:
    if 'ERROR at' in line or 'FAILED tests/' in line:
        print(line.strip()[:150])
