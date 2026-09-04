import json
import sys
from collections import Counter

path = sys.argv[1] if len(sys.argv) > 1 else "data/processed_logs.jsonl"
required = {"event_id", "normalized_timestamp", "component", "message", "parsed_message_type"}

count = 0
components = Counter()
types = Counter()
bad_json = 0
missing = Counter()

with open(path, encoding="utf-8") as f:
    for line_no, line in enumerate(f, 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            bad_json += 1
            continue
        count += 1
        components[row.get("component", "MISSING")] += 1
        types[row.get("parsed_message_type", "MISSING")] += 1
        for key in required - row.keys():
            missing[key] += 1

print(f"records: {count:,}")
print(f"invalid JSON lines: {bad_json:,}")
print(f"components: {len(components):,}")
print("top components:")
for k, v in components.most_common(10):
    print(f"  {k}: {v:,}")
print("top message types:")
for k, v in types.most_common(10):
    print(f"  {k}: {v:,}")
print("missing required fields:")
for k, v in missing.items():
    print(f"  {k}: {v:,}")
