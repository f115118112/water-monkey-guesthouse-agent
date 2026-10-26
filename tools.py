"""Tools for the Water Monkey Guesthouse customer service agent.

The CSV files are loaded into a SQLite database (guesthouse.db).
Every tool reads from that database and returns a dict, which the model
turns into a reply for the guest.
"""

import csv
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "guesthouse.db"

DISCOUNT_MIN_NIGHTS = 3      # 3 nights or more ...
DISCOUNT_RATE = 0.10         # ... get 10% off the room price
EXTRA_BED_PRICE = 500        # NT$ per night, Family rooms only
PET_FEE = 300                # NT$ per stay, pet-friendly rooms only


# ---------- database ----------

def build_database():
    """Create guesthouse.db from the two CSV files (runs again on every start)."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DROP TABLE IF EXISTS guesthouse_info")
    conn.execute("DROP TABLE IF EXISTS rooms")
    conn.execute("CREATE TABLE guesthouse_info (topic TEXT PRIMARY KEY, content TEXT)")
    conn.execute(
        "CREATE TABLE rooms (room_no TEXT PRIMARY KEY, room_type TEXT, room_type_zh TEXT, "
        "max_guests INTEGER, price_per_night INTEGER, view TEXT, pet_friendly TEXT, available TEXT)"
    )
    with open(BASE_DIR / "guesthouse_info.csv", encoding="utf-8-sig") as f:
        rows = [(r["topic"], r["content"]) for r in csv.DictReader(f)]
    conn.executemany("INSERT INTO guesthouse_info VALUES (?, ?)", rows)
    with open(BASE_DIR / "rooms.csv", encoding="utf-8-sig") as f:
        rows = [
            (r["room_no"], r["room_type"], r["room_type_zh"], int(r["max_guests"]),
             int(r["price_per_night"]), r["view"], r["pet_friendly"], r["available"])
            for r in csv.DictReader(f)
        ]
    conn.executemany("INSERT INTO rooms VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)
    conn.commit()
    conn.close()


def _query(sql, params=()):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    conn.close()
    return rows


def _clean(text):
    """Make names forgiving: ignore case, spaces, dashes and the word 'room'."""
    text = str(text).lower().strip()
    for word in ["rooms", "room", "-", "_", " "]:
        text = text.replace(word, "")
    return text


# ---------- tool 1: look up information ----------

def get_info(topic: str) -> dict:
    """Look up guesthouse information such as check-in time, address, parking,
    breakfast, payment, cancellation, discount, pets, wifi, smoking or contact.

    Args:
        topic: One topic word, for example "parking" or "check_in".
    """
    topics = [r["topic"] for r in _query("SELECT topic FROM guesthouse_info")]
    wanted = _clean(topic)
    for t in topics:
        if _clean(t) == wanted or wanted in _clean(t) or _clean(t) in wanted:
            row = _query("SELECT content FROM guesthouse_info WHERE topic = ?", (t,))[0]
            return {"found": True, "topic": t, "content": row["content"]}
    return {
        "found": False,
        "message": f"No information about '{topic}'.",
        "available_topics": topics,
    }


# ---------- tool 2: look up records ----------

def search_rooms(keyword: str = "", guests: int = 0, available_only: bool = False) -> dict:
    """Search the room list by room type, view or feature, number of guests,
    and whether the room is free.

    Args:
        keyword: Room type or feature, for example "family", "river", "twin",
            "pet" or "家庭房". Leave empty to list all rooms.
        guests: Number of guests who will stay. 0 means any number.
        available_only: True to show only rooms that are free now.
    """
    rooms = _query("SELECT * FROM rooms")
    word = _clean(keyword)
    results = []
    for r in rooms:
        if word:
            if word in ("pet", "pets", "dog", "cat", "寵物"):
                if r["pet_friendly"] != "yes":
                    continue
            elif word not in _clean(r["room_type"]) and word not in _clean(r["room_type_zh"]) \
                    and word != _clean(r["view"]) and word != r["room_no"]:
                continue
        if guests and r["max_guests"] < guests:
            continue
        if available_only and r["available"] != "yes":
            continue
        results.append(r)
    if not results:
        return {"found": False, "message": "No room matches this search."}
    return {"found": True, "count": len(results), "rooms": results}


# ---------- tool 3: calculate ----------

def calculate_stay(room: str, nights: int, extra_beds: int = 0, with_pet: bool = False) -> dict:
    """Calculate the total price of a stay.

    Formula: price per night x nights, then 10% off the room price for 3 or
    more nights, plus NT$500 per extra bed per night (Family rooms only),
    plus a NT$300 pet fee (pet-friendly rooms only).

    Args:
        room: A room number such as "203", or a room type such as "Family".
        nights: Number of nights.
        extra_beds: Number of extra beds (0 if none).
        with_pet: True if the guest brings a pet.
    """
    if nights < 1:
        return {"ok": False, "message": "The number of nights must be 1 or more."}

    # Find the room: first by room number, then by room type (English or Chinese).
    matches = _query("SELECT * FROM rooms WHERE room_no = ?", (str(room).strip(),))
    if not matches:
        word = _clean(room)
        matches = [r for r in _query("SELECT * FROM rooms")
                   if word and (word == _clean(r["room_type"]) or word == _clean(r["room_type_zh"]))]
    if not matches:
        return {"ok": False, "message": f"There is no room called '{room}'.",
                "room_types": sorted({r["room_type"] for r in _query("SELECT room_type FROM rooms")})}

    prices = sorted({r["price_per_night"] for r in matches})
    if len(prices) > 1:
        return {"ok": False, "message": f"'{room}' has more than one price. Please choose a room.",
                "choices": [{"room_no": r["room_no"], "price_per_night": r["price_per_night"],
                             "view": r["view"]} for r in matches]}
    r = matches[0]

    if extra_beds and "family" not in r["room_type"].lower():
        return {"ok": False, "message": "Extra beds are only available in Family and Family Suite rooms."}
    if with_pet and not any(m["pet_friendly"] == "yes" for m in matches):
        return {"ok": False, "message": f"Pets are not allowed in {r['room_type']} room(s) {', '.join(m['room_no'] for m in matches)}."}

    room_total = r["price_per_night"] * nights
    discount = round(room_total * DISCOUNT_RATE) if nights >= DISCOUNT_MIN_NIGHTS else 0
    extra_bed_total = EXTRA_BED_PRICE * extra_beds * nights
    pet_fee = PET_FEE if with_pet else 0
    total = room_total - discount + extra_bed_total + pet_fee

    return {
        "ok": True,
        "room": f"{r['room_type']} ({', '.join(m['room_no'] for m in matches)})",
        "price_per_night": r["price_per_night"],
        "nights": nights,
        "room_total": room_total,
        "discount": discount,
        "extra_bed_total": extra_bed_total,
        "pet_fee": pet_fee,
        "total": total,
        "deposit_30_percent": round(total * 0.3),
    }


# ---------- tool 4: hand over to a person ----------

def transfer_to_human(reason: str = "") -> dict:
    """Hand the guest over to the owner. Use this for complaints, special
    requests, and questions the other tools cannot answer.

    Args:
        reason: A short note on why the guest needs a person.
    """
    contact = _query("SELECT content FROM guesthouse_info WHERE topic = 'contact'")[0]["content"]
    return {"transferred": True, "reason": reason, "contact": contact}


TOOLS = [get_info, search_rooms, calculate_stay, transfer_to_human]

build_database()
