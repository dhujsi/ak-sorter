#!/usr/bin/env python
"""Extract Arknights operator data and prepare assets."""
import json
import os
import shutil
import sys

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

BASE = os.path.dirname(os.path.abspath(__file__))
AKR = os.path.join(BASE, 'ak-sorter-assets', 'ArknightsGameResource')
CHAR_TABLE = os.path.join(AKR, 'gamedata', 'excel', 'character_table.json')
FILE_DICT = os.path.join(AKR, 'file_dict.json')
ASSETS_AK = os.path.join(BASE, 'assets', 'ak')
AVATAR_DIR = os.path.join(ASSETS_AK, 'avatar')
PORTRAIT_DIR = os.path.join(ASSETS_AK, 'portrait')
DATA_DIR = os.path.join(ASSETS_AK, 'data')

os.makedirs(AVATAR_DIR, exist_ok=True)
os.makedirs(PORTRAIT_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# Load character table
with open(CHAR_TABLE, 'r', encoding='utf-8') as f:
    char_table = json.load(f)

def is_valid_operator(char_id, char_data):
    """Check if this is a valid playable operator."""
    profession = char_data.get('profession', '')
    if profession in ['TOKEN', 'TRAP']:
        return False
    return True

# Build operator list
operators = []
skipped = []
missing_avatar = []
missing_portrait = []
copied_avatars = 0
copied_portraits = 0

for char_id, char_data in char_table.items():
    if not is_valid_operator(char_id, char_data):
        skipped.append(char_id)
        continue

    rarity = char_data.get('rarity', 0)  # 0-5
    star = rarity + 1  # Convert to 1-6 star display

    name_cn = char_data.get('name', char_id)
    appellation = char_data.get('appellation', name_cn)

    operator = {
        'id': char_id,
        'name': name_cn,
        'appellation': appellation,
        'star': star,
        'profession': char_data.get('profession', ''),
        'subProfession': char_data.get('subProfessionId', ''),
    }
    operators.append(operator)

    # Copy avatar image (base avatar uses .png without suffix)
    avatar_src = os.path.join(AKR, 'avatar', f'{char_id}.png')
    avatar_dst = os.path.join(AVATAR_DIR, f'{char_id}.png')

    if os.path.exists(avatar_src):
        shutil.copy2(avatar_src, avatar_dst)
        copied_avatars += 1
    else:
        # Try _1.png as fallback
        avatar_src2 = os.path.join(AKR, 'avatar', f'{char_id}_1.png')
        if os.path.exists(avatar_src2):
            shutil.copy2(avatar_src2, avatar_dst)
            copied_avatars += 1
        else:
            missing_avatar.append(char_id)

    # Copy portrait image (portraits use _1.png suffix for base)
    portrait_src = os.path.join(AKR, 'portrait', f'{char_id}_1.png')
    portrait_dst = os.path.join(PORTRAIT_DIR, f'{char_id}.png')

    if os.path.exists(portrait_src):
        shutil.copy2(portrait_src, portrait_dst)
        copied_portraits += 1
    else:
        missing_portrait.append(char_id)

# Sort operators by star (ascending) then by name
operators.sort(key=lambda x: (x['star'], x['id']))

# Save operator data
output_path = os.path.join(DATA_DIR, 'operators.json')
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(operators, f, ensure_ascii=False, indent=2)

# Print summary
star_dist = {}
for op in operators:
    s = op['star']
    star_dist[s] = star_dist.get(s, 0) + 1

summary = f"""Operator extraction complete:
  Total operators: {len(operators)}
  Skipped (tokens/traps): {len(skipped)}
  Avatars copied: {copied_avatars}
  Portraits copied: {copied_portraits}
  Missing avatars: {len(missing_avatar)}
  Missing portraits: {len(missing_portrait)}

Star distribution:
"""
for s in sorted(star_dist.keys()):
    summary += f'  {s}-star: {star_dist[s]}\n'

with open(os.path.join(BASE, 'build_summary.txt'), 'w', encoding='utf-8') as f:
    f.write(summary)

print(summary)

if missing_avatar:
    print(f'Missing avatars (no file found): {len(missing_avatar)}')
    for cid in missing_avatar[:10]:
        print(f'  {cid}')
if missing_portrait:
    print(f'Missing portraits (no file found): {len(missing_portrait)}')
    for cid in missing_portrait[:10]:
        print(f'  {cid}')
