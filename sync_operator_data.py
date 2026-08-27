#!/usr/bin/env python3
"""Lightweight remote sync for Arknights operator data and missing images."""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "assets", "ak", "data")
AVATAR_DIR = os.path.join(BASE, "assets", "ak", "avatar")
PORTRAIT_DIR = os.path.join(BASE, "assets", "ak", "portrait")
OPERATORS_PATH = os.path.join(DATA_DIR, "operators.json")

UPSTREAM = "https://raw.githubusercontent.com/yuanyan3060/ArknightsGameResource/main"
CHAR_TABLE_URL = f"{UPSTREAM}/gamedata/excel/character_table.json"
AVATAR_URL = f"{UPSTREAM}/avatar"
PORTRAIT_URL = f"{UPSTREAM}/portrait"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(AVATAR_DIR, exist_ok=True)
os.makedirs(PORTRAIT_DIR, exist_ok=True)

HEADERS = {"User-Agent": "ak-sorter-auto-sync/1.0"}


def fetch_bytes(url: str, *, retries: int = 3, allow_404: bool = False) -> bytes | None:
    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 404 and allow_404:
                return None
            last_error = exc
        except Exception as exc:
            last_error = exc
        if attempt + 1 < retries:
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Failed to fetch {url}: {last_error}")


def download_if_missing(dest: str, candidates: list[str]) -> bool:
    if os.path.exists(dest):
        return False
    for url in candidates:
        data = fetch_bytes(url, allow_404=True)
        if data is not None:
            with open(dest, "wb") as f:
                f.write(data)
            return True
    return False


def is_valid_operator(char_data: dict) -> bool:
    return char_data.get("profession", "") not in {"TOKEN", "TRAP"}


old_count = 0
if os.path.exists(OPERATORS_PATH):
    try:
        with open(OPERATORS_PATH, "r", encoding="utf-8") as f:
            old_count = len(json.load(f))
    except Exception:
        pass

raw = fetch_bytes(CHAR_TABLE_URL)
if raw is None:
    raise RuntimeError("character_table.json download unexpectedly returned no data")
char_table = json.loads(raw.decode("utf-8"))

operators = []
for char_id, char_data in char_table.items():
    if not is_valid_operator(char_data):
        continue
    rarity = char_data.get("rarity", 0)
    operators.append(
        {
            "id": char_id,
            "name": char_data.get("name", char_id),
            "appellation": char_data.get("appellation", char_data.get("name", char_id)),
            "star": rarity + 1,
            "profession": char_data.get("profession", ""),
            "subProfession": char_data.get("subProfessionId", ""),
        }
    )

operators.sort(key=lambda x: (x["star"], x["id"]))

# Guard against committing a broken/truncated upstream response.
if old_count and len(operators) < max(50, int(old_count * 0.90)):
    raise RuntimeError(
        f"Refusing suspicious shrink: old={old_count}, new={len(operators)}"
    )

new_avatars = 0
new_portraits = 0
missing_avatars = []
missing_portraits = []

for op in operators:
    char_id = op["id"]

    avatar_dest = os.path.join(AVATAR_DIR, f"{char_id}.png")
    if download_if_missing(
        avatar_dest,
        [
            f"{AVATAR_URL}/{char_id}.png",
            f"{AVATAR_URL}/{char_id}_1.png",
        ],
    ):
        new_avatars += 1
    elif not os.path.exists(avatar_dest):
        missing_avatars.append(char_id)

    portrait_dest = os.path.join(PORTRAIT_DIR, f"{char_id}.png")
    if download_if_missing(
        portrait_dest,
        [f"{PORTRAIT_URL}/{char_id}_1.png"],
    ):
        new_portraits += 1
    elif not os.path.exists(portrait_dest):
        missing_portraits.append(char_id)

with open(OPERATORS_PATH, "w", encoding="utf-8") as f:
    json.dump(operators, f, ensure_ascii=False, indent=2)
    f.write("\n")

print(f"Operators: {old_count} -> {len(operators)}")
print(f"Downloaded avatars: {new_avatars}")
print(f"Downloaded portraits: {new_portraits}")
print(f"Missing avatars: {len(missing_avatars)}")
print(f"Missing portraits: {len(missing_portraits)}")

if missing_avatars:
    print("Missing avatar IDs:", ", ".join(missing_avatars[:20]))
if missing_portraits:
    print("Missing portrait IDs:", ", ".join(missing_portraits[:20]))
