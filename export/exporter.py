import csv
import io
import json


## rows -> CSV text
def make_csv(rows):
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["task_id", "text", "label", "label_source"])
    for r in rows:
        writer.writerow([r["task_id"], r["text"], r["label"], r["label_source"]])

    return output.getvalue()


## rows -> JSONL text (one JSON object per line)
def make_jsonl(rows):
    lines = []
    for r in rows:
        lines.append(json.dumps(r, ensure_ascii=False))
    return "\n".join(lines) + "\n"