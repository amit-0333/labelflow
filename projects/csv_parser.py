import csv
import io


## reads an uploaded CSV file
## returns (tasks, error). If something is wrong, tasks is None and error has the reason
def parse_csv(file):
    try:
        content = file.read().decode('utf-8-sig')
    except UnicodeDecodeError:
        return None, "Save the file as UTF-8 and try again"

    reader = csv.DictReader(io.StringIO(content))

    if reader.fieldnames is None or 'text' not in reader.fieldnames:
        return None, "CSV must have a column named text"

    tasks = []
    for row in reader:
        text = (row.get('text') or '').strip()
        if text == '':
            continue

        ## optional column: the correct answer for a gold question
        gold_label = (row.get('gold_label') or '').strip()
        if gold_label == '':
            gold_label = None

        ## all other columns are saved as extra data
        extra = {}
        for key, value in row.items():
            if key not in ('text', 'gold_label') and key is not None:
                extra[key] = value

        tasks.append({"text": text, "gold_label": gold_label, "extra": extra})

    if len(tasks) == 0:
        return None, "No rows found in the file"

    return tasks, None