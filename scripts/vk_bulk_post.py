#!/usr/bin/env python3
import json, os, sys, time, urllib.parse, urllib.request

API = "https://api.vk.com/method/"
VERSION = "5.199"
GROUP_ID = 240853168

def api(method, params):
    params = dict(params)
    params["access_token"] = TOKEN
    params["v"] = VERSION
    data = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(API + method, data=data)
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.loads(r.read().decode("utf-8"))
    if "error" in payload:
        e = payload["error"]
        raise RuntimeError(f"{method}: VK error {e.get('error_code')}: {e.get('error_msg')}")
    return payload["response"]

TOKEN = os.environ.get("VK_GROUP_TOKEN", "").strip()
if not TOKEN:
    print("VK_GROUP_TOKEN secret is missing", file=sys.stderr)
    sys.exit(2)

start_index = int(os.environ.get("START_INDEX", "1"))
count = int(os.environ.get("COUNT", "1"))
interval_minutes = int(os.environ.get("INTERVAL_MINUTES", "10"))
first_delay_minutes = int(os.environ.get("FIRST_DELAY_MINUTES", "3"))

with open("data/vk_posts.json", "r", encoding="utf-8") as f:
    plan = json.load(f)

posts = plan["posts"]
selected = [p for p in posts if p["number"] >= start_index][:count]
if not selected:
    raise RuntimeError("No posts selected. Check START_INDEX and COUNT.")

# Read market items already imported into the community.
market = api("market.get", {
    "owner_id": -GROUP_ID,
    "count": 200,
    "offset": 0,
    "extended": 0,
})
items = market.get("items", [])
by_title = {str(x.get("title","")).strip().casefold(): x for x in items}

missing = [p["title"] for p in selected if p["title"].strip().casefold() not in by_title]
if missing:
    print("Could not match these posts to VK market items:", file=sys.stderr)
    for x in missing:
        print(" - " + x, file=sys.stderr)
    sys.exit(3)

now = int(time.time())
print(f"Matched {len(selected)} posts to VK market items.")

for pos, p in enumerate(selected):
    item = by_title[p["title"].strip().casefold()]
    publish_ts = now + first_delay_minutes*60 + pos*interval_minutes*60
    attachment = f"market-{GROUP_ID}_{item['id']}"
    guid = f"torty-saransk-{p['number']:03d}-{publish_ts}"
    resp = api("wall.post", {
        "owner_id": -GROUP_ID,
        "from_group": 1,
        "message": p["text"],
        "attachments": attachment,
        "publish_date": publish_ts,
        "guid": guid,
        "mute_notifications": 1,
    })
    print(f"#{p['number']:03d} scheduled: {p['title']} -> post_id={resp.get('post_id')} at {publish_ts}")
    time.sleep(0.6)

print("Done.")
