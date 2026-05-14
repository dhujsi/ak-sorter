#!/usr/bin/env python
"""Map PRTS halfbody portraits to operator IDs and copy into assets/ak/portrait/."""
import csv
import json
import os
import re
import shutil
import sys

sys.stdout.reconfigure(encoding='utf-8')

BASE = os.path.dirname(os.path.abspath(__file__))
PRTS_DIR = os.path.join(BASE, 'assets', 'prts', 'halfbody')
PRTS_CSV = os.path.join(BASE, 'prts_halfbody_manifest.csv')
OP_JSON = os.path.join(BASE, 'assets', 'ak', 'data', 'operators.json')
PORTRAIT_DIR = os.path.join(BASE, 'assets', 'ak', 'portrait')

# Load operators
with open(OP_JSON, 'r', encoding='utf-8') as f:
    operators = json.load(f)

# Load PRTS manifest - build set of (name, number) tuples
prts_files = {}
with open(PRTS_CSV, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        fname = row['name']
        # Parse: 半身像_<opname>_<variant>.png
        m = re.match(r'半身像_(.+)_(\d+)\.png', fname)
        if m:
            opname = m.group(1)
            variant = int(m.group(2))
            if opname not in prts_files:
                prts_files[opname] = {}
            prts_files[opname][variant] = fname

# Build mapping
print(f'Operators: {len(operators)}')
print(f'PRTS names: {len(prts_files)}')
print()

# Clean up old portraits
if os.path.exists(PORTRAIT_DIR):
    for f in os.listdir(PORTRAIT_DIR):
        os.remove(os.path.join(PORTRAIT_DIR, f))

# Match operators to PRTS files
matched = 0
unmatched = []
matched_by_name = 0
matched_by_appellation = 0

for op in operators:
    op_id = op['id']
    name_cn = op.get('name', '')
    appellation = op.get('appellation', '')
    star = op.get('star', 0)

    # Try matching
    prts_name = None
    match_type = None

    # Step 1: match by Chinese name
    if name_cn in prts_files:
        prts_name = name_cn
        match_type = 'name'
        matched_by_name += 1
    # Step 2: match by appellation (for robots and English-named ops)
    elif appellation in prts_files:
        prts_name = appellation
        match_type = 'appellation'
        matched_by_appellation += 1
    # Step 3: try name without parenthetical suffix (for alters)
    elif name_cn not in prts_files and appellation not in prts_files:
        # Try fuzzy: check if any PRTS name contains our name as substring
        # This helps with cases like "阿米娅(近卫)" vs operator name
        pass

    # If no direct match, try with (卫戍协议) suffix for NPC-category operators
    if not prts_name:
        garrison_name = f'{name_cn}(卫戍协议)'
        if garrison_name in prts_files:
            prts_name = garrison_name
            match_type = 'garrison'
        elif f'{appellation}(卫戍协议)' in prts_files:
            prts_name = f'{appellation}(卫戍协议)'
            match_type = 'garrison'

    if prts_name and 1 in prts_files[prts_name]:
        src_file = os.path.join(PRTS_DIR, prts_files[prts_name][1])
        dst_file = os.path.join(PORTRAIT_DIR, f'{op_id}.png')
        if os.path.exists(src_file):
            shutil.copy2(src_file, dst_file)
            matched += 1
            if match_type == 'garrison':
                print(f'  GARRISON: {op_id} ({name_cn}) <- {prts_name}')
        else:
            print(f'  MISSING FILE: {src_file}')
            unmatched.append(f'{op_id} ({name_cn} / {appellation}) — PRTS file not found on disk')
    else:
        unmatched.append(f'{op_id} ({name_cn} / {appellation}) — no PRTS match')

# Report
print(f'Matched: {matched}/{len(operators)}')
print(f'  by Chinese name: {matched_by_name}')
print(f'  by appellation: {matched_by_appellation}')
print(f'Unmatched: {len(unmatched)}')

if unmatched:
    print('\nUnmatched operators:')
    for u in unmatched:
        print(f'  {u}')

# Final unmatched report - these have no PRTS portraits at all
if unmatched:
    remaining = []
    for entry in unmatched:
        op_id = entry.split()[0]
        op = next((o for o in operators if o['id'] == op_id), None)
        if op:
            remaining.append(f'{op_id} ({op["name"]} / {op["appellation"]}) — star {op["star"]}')
    unmatched = remaining

print(f'\nFinal: {matched} matched, {len(unmatched)} unmatched')
if unmatched:
    print('Remaining unmatched:')
    for u in unmatched:
        print(f'  {u}')

# Save mapping report
report_path = os.path.join(BASE, 'prts_mapping_report.txt')
with open(report_path, 'w', encoding='utf-8') as f:
    f.write(f'PRTS Portrait Mapping Report\n')
    f.write(f'============================\n')
    f.write(f'Matched: {matched}/{len(operators)}\n')
    f.write(f'  by name: {matched_by_name}\n')
    f.write(f'  by appellation: {matched_by_appellation}\n')
    if unmatched:
        f.write(f'\nUnmatched ({len(unmatched)}):\n')
        for u in unmatched:
            f.write(f'  {u}\n')

print(f'\nReport saved to {report_path}')
