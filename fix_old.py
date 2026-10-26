from app import app
from core.models import Task
from tasks.review import check_task

with app.app_context():
    for t in Task.query.all():
        check_task(t.id)
    print("done")