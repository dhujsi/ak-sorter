#!/usr/bin/env python3
"""Sync Arknights operators, base images, latest-skin avatars, and true PRTS halfbody portraits."""
from __future__ import annotations

import csv
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "assets", "ak", "data")
AVATAR_DIR = os.path.join(BASE, "assets", "ak", "avatar")
PORTRAIT_DIR = os.path.join(BASE, "assets", "ak", "portrait")
SKIN_AVATAR_DIR = os.path.join(BASE, "assets", "ak", "skin-avatar")
SKIN_PORTRAIT_DIR = os.path.join(BASE, "assets", "ak", "skin-portrait")
OPERATORS_PATH = os.path.join(DATA_DIR, "operators.json")
LATEST_SKINS_PATH = os.path.join(DATA_DIR, "latest_skins.json")
PRTS_MANIFEST_PATH = os.path.join(BASE, "prts_halfbody_manifest.csv")

UPSTREAM = "https://raw.githubusercontent.com/yuanyan3060/ArknightsGameResource/main"
CHAR_TABLE_URL = f"{UPSTREAM}/gamedata/excel/character_table.json"
SKIN_TABLE_URL = f"{UPSTREAM}/gamedata/excel/skin_table.json"
AVATAR_URL = f"{UPSTREAM}/avatar"
PORTRAIT_URL = f"{UPSTREAM}/portrait"
PRTS_API = "https://prts.wiki/api.php"

for path in (DATA_DIR, AVATAR_DIR, PORTRAIT_DIR, SKIN_AVATAR_DIR, SKIN_PORTRAIT_DIR):
    os.makedirs(path, exist_ok=True)

HEADERS = {
    "User-Agent": "ak-sorter-auto-sync/2.1 (+https://github.com/dhujsi/ak-sorter)"
}


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


def load_prts_manifest_fallback() -> dict[str, str]:
    """Load the committed PRTS manifest as a fallback if the live MediaWiki API is unavailable."""
    images: dict[str, str] = {}
    try:
        with open(PRTS_MANIFEST_PATH, "r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                name = row.get("name") or ""
                url = row.get("url") or ""
                if name.startswith("半身像_") and url:
                    images[name] = url
    except OSError:
        pass
    return images


def fetch_prts_halfbody_index() -> tuple[dict[str, str], str]:
    """Fetch all PRTS halfbody file names in a few paginated MediaWiki API requests."""
    images: dict[str, str] = {}
    continuation: dict[str, str] = {}
    try:
        while True:
            params = {
                "action": "query",
                "format": "json",
                "formatversion": "2",
                "list": "allimages",
                "aiprefix": "半身像_",
                "ailimit": "500",
                "aiprop": "url",
                **continuation,
            }
            url = PRTS_API + "?" + urllib.parse.urlencode(params)
            data = fetch_json(url)
            for item in ((data.get("query") or {}).get("allimages") or []):
                name = item.get("name")
                image_url = item.get("url")
                if name and image_url:
                    images[name] = image_url

            cont = data.get("continue")
            if not cont:
                break
            continuation = {str(k): str(v) for k, v in cont.items()}

        if images:
            return images, "live"
    except Exception as exc:
        print(f"PRTS live index unavailable, using committed manifest: {exc}")

    return load_prts_manifest_fallback(), "manifest"


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

# Determine each operator's latest skin and its chronological skin number.
skin_table = fetch_json(SKIN_TABLE_URL)
char_skins = skin_table.get("charSkins", {})
if not isinstance(char_skins, dict):
    raise RuntimeError("skin_table.json has no charSkins mapping")

now = int(time.time())
released_skins_by_char: dict[str, list[dict]] = defaultdict(list)

for skin in char_skins.values():
    if not isinstance(skin, dict):
        continue
    char_id = skin.get("charId")
    skin_id = skin.get("skinId")
    display = skin.get("displaySkin") or {}
    if not char_id or not skin_id or "@" not in skin_id or not isinstance(display, dict):
        continue

    try:
        get_time = int(display.get("getTime", 0) or 0)
    except (TypeError, ValueError):
        get_time = 0
    if get_time <= 0 or get_time > now:
        continue

    try:
        sort_id = int(display.get("sortId", 0) or 0)
    except (TypeError, ValueError):
        sort_id = 0

    released_skins_by_char[char_id].append(
        {
            "skinId": skin_id,
            "assetId": skin_id.replace("@", "_"),
            "getTime": get_time,
            "sortId": sort_id,
            "skinName": display.get("skinName") or "",
        }
    )

latest_by_char: dict[str, dict] = {}
for char_id, skins in released_skins_by_char.items():
    skins.sort(key=lambda s: (s["getTime"], s["sortId"], s["skinId"]))
    for index, skin in enumerate(skins, start=1):
        skin["skinIndex"] = index
    latest_by_char[char_id] = skins[-1]

prts_images, prts_index_source = fetch_prts_halfbody_index()
print(f"PRTS halfbody index: {len(prts_images)} files ({prts_index_source})")

old_skin_manifest = load_json_file(LATEST_SKINS_PATH, {})
if not isinstance(old_skin_manifest, dict):
    old_skin_manifest = {}

operator_by_id = {op["id"]: op for op in operators}
operator_ids = set(operator_by_id)
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
    skin_changed = old.get("skinId") != skin["skinId"]
    asset_id = skin["assetId"]
    asset_url_id = urllib.parse.quote(asset_id, safe="")

    # Latest-skin avatar comes directly from the game resource.
    if skin_changed or not os.path.exists(avatar_dest):
        if download_replace(avatar_dest, [f"{AVATAR_URL}/{asset_url_id}.png"]):
            skin_avatar_updates += 1
        else:
            remove_if_exists(avatar_dest)

    # PRTS provides actual 180x360-style halfbody portraits.
    # Require the exact chronological skin number so we never substitute an older skin.
    op = operator_by_id[char_id]
    skin_index = skin["skinIndex"]
    prts_file = None
    prts_url = None
    for display_name in dict.fromkeys([op.get("name", ""), op.get("appellation", "")]):
        if not display_name:
            continue
        candidate = f"半身像_{display_name}_skin{skin_index}.png"
        if candidate in prts_images:
            prts_file = candidate
            prts_url = prts_images[candidate]
            break

    portrait_changed = (
        skin_changed
        or old.get("portraitSource") != "prts-halfbody"
        or old.get("portraitFile") != prts_file
    )

    if prts_url:
        if portrait_changed or not os.path.exists(portrait_dest):
            if download_replace(portrait_dest, [prts_url]):
                skin_portrait_updates += 1
            else:
                remove_if_exists(portrait_dest)
    else:
        # Important: do not keep the previous full-body/older-skin image.
        remove_if_exists(portrait_dest)

    has_avatar = os.path.exists(avatar_dest)
    has_portrait = os.path.exists(portrait_dest)
    if not has_avatar:
        skin_avatar_missing += 1
    if not has_portrait:
        skin_portrait_missing += 1

    entry = {
        **skin,
        "avatar": has_avatar,
        "portrait": has_portrait,
    }
    if has_portrait and prts_file:
        entry["portraitSource"] = "prts-halfbody"
        entry["portraitFile"] = prts_file
    new_skin_manifest[char_id] = entry

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
print(f"Updated PRTS skin halfbodies: {skin_portrait_updates}")
print(f"Latest skins without avatar: {skin_avatar_missing}")
print(f"Latest skins without PRTS halfbody: {skin_portrait_missing}")

if missing_avatars:
    print("Missing base avatar IDs:", ", ".join(missing_avatars[:20]))
if missing_portraits:
    print("Missing base portrait IDs:", ", ".join(missing_portraits[:20]))
