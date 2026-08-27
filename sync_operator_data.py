#!/usr/bin/env python3
"""Lightweight remote sync for Arknights operator data, base images, and latest skins."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
import urllib.parse

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "assets", "ak", "data")
AVATAR_DIR = os.path.join(BASE, "assets", "ak", "avatar")
PORTRAIT_DIR = os.path.join(BASE, "assets", "ak", "portrait")
SKIN_AVATAR_DIR = os.path.join(BASE, "assets", "ak", "skin-avatar")
SKIN_PORTRAIT_DIR = os.path.join(BASE, "assets", "ak", "skin-portrait")
OPERATORS_PATH = os.path.join(DATA_DIR, "operators.json")
LATEST_SKINS_PATH = os.path.join(DATA_DIR, "latest_skins.json")

UPSTREAM = "https://raw.githubusercontent.com/yuanyan3060/ArknightsGameResource/main"
CHAR_TABLE_URL = f"{UPSTREAM}/gamedata/excel/character_table.json"
SKIN_TABLE_URL = f"{UPSTREAM}/gamedata/excel/skin_table.json"
AVATAR_URL = f"{UPSTREAM}/avatar"
PORTRAIT_URL = f"{UPSTREAM}/portrait"
SKIN_URL = f"{UPSTREAM}/skin"

for path in (DATA_DIR, AVATAR_DIR, PORTRAIT_DIR, SKIN_AVATAR_DIR, SKIN_PORTRAIT_DIR):
    os.makedirs(path, exist_ok=True)

HEADERS = {"User-Agent": "ak-sorter-auto-sync/2.0"}


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


def fetch_json(url: str) -> dict:
    raw = fetch_bytes(url)
    if raw is None:
        raise RuntimeError(f"Unexpected empty response: {url}")
    return json.loads(raw.decode("utf-8"))


def download_if_missing(dest: str, candidates: list[str]) -> bool:
    if os.path.exists(dest):
        return False
    return download_replace(dest, candidates)


def download_replace(dest: str, candidates: list[str]) -> bool:
    for url in candidates:
        data = fetch_bytes(url, allow_404=True)
        if data is not None:
            tmp = dest + ".tmp"
            with open(tmp, "wb") as f:
                f.write(data)
            os.replace(tmp, dest)
            return True
    return False


def remove_if_exists(path: str) -> None:
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def is_valid_operator(char_data: dict) -> bool:
    return char_data.get("profession", "") not in {"TOKEN", "TRAP"}


def load_json_file(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


old_operators = load_json_file(OPERATORS_PATH, [])
old_count = len(old_operators) if isinstance(old_operators, list) else 0

char_table = fetch_json(CHAR_TABLE_URL)

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

skin_table = fetch_json(SKIN_TABLE_URL)
char_skins = skin_table.get("charSkins", {})
if not isinstance(char_skins, dict):
    raise RuntimeError("skin_table.json has no charSkins mapping")

now = int(time.time())
latest_by_char: dict[str, dict] = {}
for skin in char_skins.values():
    if not isinstance(skin, dict):
        continue
    char_id = skin.get("charId")
    skin_id = skin.get("skinId")
    display = skin.get("displaySkin") or {}
    if not char_id or not skin_id or "@" not in skin_id or not isinstance(display, dict):
        continue

    get_time = display.get("getTime", 0)
    try:
        get_time = int(get_time or 0)
    except (TypeError, ValueError):
        get_time = 0
    if get_time <= 0 or get_time > now:
        continue

    sort_id = display.get("sortId", 0)
    try:
        sort_id = int(sort_id or 0)
    except (TypeError, ValueError):
        sort_id = 0

    candidate = {
        "skinId": skin_id,
        "assetId": skin_id.replace("@", "_"),
        "getTime": get_time,
        "sortId": sort_id,
        "skinName": display.get("skinName") or "",
    }
    previous = latest_by_char.get(char_id)
    if previous is None or (
        candidate["getTime"],
        candidate["sortId"],
        candidate["skinId"],
    ) > (
        previous["getTime"],
        previous["sortId"],
        previous["skinId"],
    ):
        latest_by_char[char_id] = candidate

old_skin_manifest = load_json_file(LATEST_SKINS_PATH, {})
if not isinstance(old_skin_manifest, dict):
    old_skin_manifest = {}

operator_ids = {op["id"] for op in operators}
new_skin_manifest = {}
skin_avatar_updates = 0
skin_portrait_updates = 0
skin_avatar_missing = 0
skin_portrait_missing = 0

for char_id in sorted(operator_ids):
    skin = latest_by_char.get(char_id)
    avatar_dest = os.path.join(SKIN_AVATAR_DIR, f"{char_id}.png")
    portrait_dest = os.path.join(SKIN_PORTRAIT_DIR, f"{char_id}.png")

    if not skin:
        remove_if_exists(avatar_dest)
        remove_if_exists(portrait_dest)
        continue

    old = old_skin_manifest.get(char_id) or {}
    changed = old.get("skinId") != skin["skinId"]
    asset_id = skin["assetId"]
    asset_url_id = urllib.parse.quote(asset_id, safe="")

    if changed or not os.path.exists(avatar_dest):
        if download_replace(avatar_dest, [f"{AVATAR_URL}/{asset_url_id}.png"]):
            skin_avatar_updates += 1
        else:
            remove_if_exists(avatar_dest)

    if changed or not os.path.exists(portrait_dest):
        if download_replace(
            portrait_dest,
            [
                f"{SKIN_URL}/{asset_url_id}b.png",
                f"{SKIN_URL}/{asset_url_id}_spb.png",
            ],
        ):
            skin_portrait_updates += 1
        else:
            remove_if_exists(portrait_dest)

    has_avatar = os.path.exists(avatar_dest)
    has_portrait = os.path.exists(portrait_dest)
    if not has_avatar:
        skin_avatar_missing += 1
    if not has_portrait:
        skin_portrait_missing += 1

    new_skin_manifest[char_id] = {
        **skin,
        "avatar": has_avatar,
        "portrait": has_portrait,
    }

for directory in (SKIN_AVATAR_DIR, SKIN_PORTRAIT_DIR):
    for name in os.listdir(directory):
        if not name.endswith(".png"):
            continue
        char_id = name[:-4]
        if char_id not in operator_ids:
            remove_if_exists(os.path.join(directory, name))

with open(LATEST_SKINS_PATH, "w", encoding="utf-8") as f:
    json.dump(new_skin_manifest, f, ensure_ascii=False, indent=2)
    f.write("\n")

print(f"Operators: {old_count} -> {len(operators)}")
print(f"Downloaded base avatars: {new_avatars}")
print(f"Downloaded base portraits: {new_portraits}")
print(f"Missing base avatars: {len(missing_avatars)}")
print(f"Missing base portraits: {len(missing_portraits)}")
print(f"Released latest skins: {len(new_skin_manifest)}")
print(f"Updated skin avatars: {skin_avatar_updates}")
print(f"Updated skin portraits: {skin_portrait_updates}")
print(f"Latest skins without avatar: {skin_avatar_missing}")
print(f"Latest skins without portrait: {skin_portrait_missing}")

if missing_avatars:
    print("Missing base avatar IDs:", ", ".join(missing_avatars[:20]))
if missing_portraits:
    print("Missing base portrait IDs:", ", ".join(missing_portraits[:20]))
