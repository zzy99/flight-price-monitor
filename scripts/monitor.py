#!/usr/bin/env python3
"""Daily FlyAI flight price checker for GitHub Actions."""
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "data" / "prices.json"
FLYAI_BIN = os.getenv("FLYAI_BIN", "flyai.cmd" if os.name == "nt" else "flyai")
FLIGHTS = (
    {"number": "HO1229", "origin": "上海", "destination": "丽江", "date": "2026-09-12"},
    {"number": "MU9703", "origin": "大理", "destination": "上海", "date": "2026-09-18"},
)


def query(spec):
    command = [FLYAI_BIN, "search-flight", "--origin", spec["origin"], "--destination", spec["destination"], "--dep-date", spec["date"], "--journey-type", "1", "--transport-no", spec["number"], "--sort-type", "3"]
    result = subprocess.run(command, capture_output=True, timeout=90, check=False)
    stdout = result.stdout.decode("utf-8", errors="replace")
    stderr = result.stderr.decode("utf-8", errors="replace")
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"invalid FlyAI JSON: {stderr[-300:]}") from error
    offers = []
    for item in data.get("data", {}).get("itemList", []):
        for journey in item.get("journeys", []):
            for segment in journey.get("segments", []):
                if segment.get("marketingTransportNo", "").upper() != spec["number"]:
                    continue
                try:
                    price = float(item["ticketPrice"])
                except (KeyError, TypeError, ValueError):
                    continue
                offers.append({"price": price, "cabin": segment.get("seatClassName", "未知舱位"), "departure": segment.get("depDateTime", ""), "arrival": segment.get("arrDateTime", ""), "jump_url": item.get("jumpUrl", "")})
    if not offers:
        raise RuntimeError("no fare returned")
    return {**spec, **min(offers, key=lambda item: item["price"])}


def load_history():
    try:
        return json.loads(HISTORY.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"flights": {}}


def post(url, body):
    request = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode(), headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=20) as response:
        response.read()


def notify(text):
    if sendkey := os.getenv("SERVERCHAN_SENDKEY"):
        post(f"https://sctapi.ftqq.com/{sendkey}.send", {"title": "每日航班价格监控", "desp": text})
    if url := os.getenv("FEISHU_WEBHOOK_URL"):
        post(url, {"msg_type": "text", "content": {"text": text}})
    if url := os.getenv("WECHAT_WORK_WEBHOOK_URL"):
        post(url, {"msgtype": "text", "text": {"content": text}})


def clock(value):
    return value[11:16] if len(value) >= 16 else value


def main():
    history = load_history()
    previous = history.setdefault("flights", {})
    rows, errors = [], []
    for spec in FLIGHTS:
        try:
            current = query(spec)
            old = previous.get(spec["number"], {}).get("price")
            change = "首次记录" if old is None else ("价格不变" if float(old) == current["price"] else f"{'降价' if current['price'] < float(old) else '涨价'} ¥{abs(current['price'] - float(old)):.0f}")
            current["checked_at"] = datetime.now(timezone.utc).isoformat()
            previous[spec["number"]] = current
            rows.append((current, change))
        except Exception as error:
            errors.append(f"{spec['number']}: {error}")
    HISTORY.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["✈️ 每日航班价格监控", ""]
    for current, change in rows:
        lines += [f"{current['number']}  {current['origin']}→{current['destination']}  {current['date']}", f"¥{current['price']:.0f} · {current['cabin']} · {clock(current['departure'])}–{clock(current['arrival'])}", change, current["jump_url"], ""]
    if errors:
        lines += ["⚠️ 查询失败", *errors]
    message = "\n".join(lines).strip()
    print(message)
    notify(message)
    return 1 if errors and not rows else 0


if __name__ == "__main__":
    sys.exit(main())
