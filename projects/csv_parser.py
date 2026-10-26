import csv
import io


## reads an uploaded CSV file
## returns (tasks, error). If something is wrong, tasks is None and error has the reason
def parse_csv(file):
    ## utf-8-sig removes the hidden mark that Excel adds at the start
    try:
        content = file.read().decode('utf-8-sig')
    except UnicodeDecodeError:
        return None, "Save the file as UTF-8 and try again"

    reader = csv.DictReader(io.StringIO(content))

    ## the CSV must have a column named text
    if reader.fieldnames is None or 'text' not in reader.fieldnames:
        return None, "CSV must have a column named text"

    tasks = []
    for row in reader:
        text = (row.get('text') or '').strip()

        ## skip empty rows
        if text == '':
            continue

        ## all other columns are saved as extra data
        extra = {}
        for key, value in row.items():
            if key != 'text' and key is not None:
                extra[key] = value

        tasks.append({"text": text, "extra": extra})

    if len(tasks) == 0:
        return None, "No rows found in the file"

    return tasks, None