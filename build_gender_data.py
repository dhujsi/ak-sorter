#!/usr/bin/env python
"""Generate operator_extra.json from arknights_operator_gender.csv."""
import csv, json, os

BASE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE, 'arknights_operator_gender.csv')
OP_PATH = os.path.join(BASE, 'assets', 'ak', 'data', 'operators.json')
OUT_PATH = os.path.join(BASE, 'assets', 'ak', 'data', 'operator_extra.json')

with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
    gender_rows = list(csv.DictReader(f))

name_to_gender = {}
for r in gender_rows:
    name = r['Name'].strip()
    g = r['Gender'].strip()
    if g == '男': name_to_gender[name] = 'male'
    elif g == '女': name_to_gender[name] = 'female'
    else: name_to_gender[name] = 'unknown'

with open(OP_PATH, 'r', encoding='utf-8') as f:
    operators = json.load(f)

extra = {}
matched = 0
for op in operators:
    name = op.get('name', '')
    gender = name_to_gender.get(name, 'unknown')
    extra[op['id']] = {'gender': gender}
    if gender != 'unknown':
        matched += 1

with open(OUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(extra, f, ensure_ascii=False, indent=2)

from collections import Counter
c = Counter(v['gender'] for v in extra.values())
print(f"Generated {OUT_PATH}")
print(f"  total: {len(extra)}, matched: {matched}, unmatched: {len(extra)-matched}")
print(f"  female: {c.get('female',0)}, male: {c.get('male',0)}, unknown: {c.get('unknown',0)}")
