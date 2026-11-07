import csv
import io

## required columns for each project type
REQUIRED = {
    "classification": ["text"],
    "pairwise": ["prompt", "answer_a", "answer_b"],
    "rating": ["prompt", "answer"],
}


## reads an uploaded CSV file
## returns (tasks, error). If something is wrong, tasks is None and error has the reason
def parse_csv(file, task_type="classification"):
    try:
        content = file.read().decode('utf-8-sig')
    except UnicodeDecodeError:
        return None, "Save the file as UTF-8 and try again"

    reader = csv.DictReader(io.StringIO(content))
    fields = reader.fieldnames or []

    needed = REQUIRED.get(task_type, ["text"])
    for col in needed:
        if col not in fields:
            return None, "CSV must have columns: " + ", ".join(needed)

    ## the main text is "text" for classification, "prompt" for the others
    text_col = "text" if task_type == "classification" else "prompt"

    tasks = []
    for row in reader:
        ## skip rows where a needed column is empty
        if any((row.get(c) or '').strip() == '' for c in needed):
            continue

        gold_label = (row.get('gold_label') or '').strip()
        if gold_label == '':
            gold_label = None

        ## everything except the main text is saved as extra data (answers, sender, ...)
        extra = {}
        for key, value in row.items():
            if key not in (text_col, 'gold_label') and key is not None:
                extra[key] = value

        tasks.append({"text": row[text_col].strip(), "gold_label": gold_label, "extra": extra})

    if len(tasks) == 0:
        return None, "No rows found in the file"

    return tasks, None