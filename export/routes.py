from flask import Blueprint, Response, abort
from core.models import Project, Task
from auth.decorators import role_required
from export.exporter import make_csv, make_jsonl

export_bp = Blueprint("export", __name__)


## admin or reviewer: download the final labels of one project
@export_bp.route('/export/<int:project_id>/<file_type>')
@role_required("admin", "reviewer")
def export_project(project_id, file_type):
    Project.query.get_or_404(project_id)

    if file_type not in ("csv", "jsonl"):
        abort(404)

    ## only finished tasks, and never the hidden gold questions
    tasks = (
        Task.query
        .filter_by(project_id=project_id, status="completed", is_gold=False)
        .order_by(Task.id)
        .all()
    )

    rows = []
    for t in tasks:
        rows.append({
            "task_id": t.id,
            "text": t.text,
            "label": t.final_label,
            "label_source": t.final_source,
            "extra": t.extra_data
        })

    if file_type == "csv":
        content = make_csv(rows)
        mimetype = "text/csv"
    else:
        content = make_jsonl(rows)
        mimetype = "application/x-ndjson"

    filename = "project_" + str(project_id) + "_final." + file_type

    return Response(
        content,
        mimetype=mimetype,
        headers={"Content-Disposition": "attachment; filename=" + filename}
    )