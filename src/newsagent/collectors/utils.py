import json

def load_channel_list(path="channel_list.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
