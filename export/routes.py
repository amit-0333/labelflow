from flask import Blueprint, Response, abort, render_template, redirect
from flask_login import current_user
from core.db import db
from core.models import Project, Task, DatasetVersion
from auth.decorators import role_required
from export.exporter import make_csv, make_jsonl

export_bp = Blueprint("export", __name__)


## final labels of a project as a list of rows (finished tasks only, never gold)
def get_final_rows(project_id):
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
    return rows


## rows -> file download
def send_file(rows, file_type, filename):
    if file_type == "csv":
        content = make_csv(rows)
        mimetype = "text/csv"
    else:
        content = make_jsonl(rows)
        mimetype = "application/x-ndjson"

    return Response(
        content,
        mimetype=mimetype,
        headers={"Content-Disposition": "attachment; filename=" + filename + "." + file_type}
    )


## admin or reviewer: download the current final labels
@export_bp.route('/export/<int:project_id>/<file_type>')
@role_required("admin", "reviewer")
def export_project(project_id, file_type):
    Project.query.get_or_404(project_id)
    if file_type not in ("csv", "jsonl"):
        abort(404)
    return send_file(get_final_rows(project_id), file_type, "project_" + str(project_id) + "_final")


## admin or reviewer: list all snapshots of a project
@export_bp.route('/versions/<int:project_id>')
@role_required("admin", "reviewer")
def versions(project_id):
    project = Project.query.get_or_404(project_id)
    all_versions = (
        DatasetVersion.query
        .filter_by(project_id=project_id)
        .order_by(DatasetVersion.version_number.desc())
        .all()
    )
    return render_template('versions.html', project=project, versions=all_versions)


## admin or reviewer: freeze the current final labels as the next version
@export_bp.route('/perform_create_version/<int:project_id>', methods=['POST'])
@role_required("admin", "reviewer")
def perform_create_version(project_id):
    Project.query.get_or_404(project_id)

    rows = get_final_rows(project_id)
    if len(rows) == 0:
        return redirect('/versions/' + str(project_id))

    last = (
        DatasetVersion.query
        .filter_by(project_id=project_id)
        .order_by(DatasetVersion.version_number.desc())
        .first()
    )
    next_number = 1 if last is None else last.version_number + 1

    version = DatasetVersion(
        project_id=project_id,
        version_number=next_number,
        row_count=len(rows),
        data=rows,
        created_by=current_user.id
    )
    db.session.add(version)
    db.session.commit()

    return redirect('/versions/' + str(project_id))


## admin or reviewer: download one frozen snapshot
@export_bp.route('/export_version/<int:version_id>/<file_type>')
@role_required("admin", "reviewer")
def export_version(version_id, file_type):
    version = DatasetVersion.query.get_or_404(version_id)
    if file_type not in ("csv", "jsonl"):
        abort(404)
    name = "project_" + str(version.project_id) + "_v" + str(version.version_number)
    return send_file(version.data, file_type, name)