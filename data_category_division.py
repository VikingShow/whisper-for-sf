import json, random

with open("manifest.jsonl", "r", encoding="utf8") as f:
    lines = f.readlines()

random.shuffle(lines)
split = int(len(lines) * 0.95)

with open("train.jsonl", "w", encoding="utf8") as f:
    f.writelines(lines[:split])

with open("valid.jsonl", "w", encoding="utf8") as f:
    f.writelines(lines[split:])
