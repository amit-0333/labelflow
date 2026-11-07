import time
from app import app
from core.db import db
from core.models import Project, Task, AIPrediction
from llm.groq_client import prelabel


## runs in the worker: asks Groq for every task that has no AI label yet
def prelabel_project(project_id):
    with app.app_context():
        project = Project.query.get(project_id)

        ## tasks that already have a prediction are skipped
        already_done = db.session.query(AIPrediction.task_id)
        tasks = (
            Task.query
            .filter(Task.project_id == project_id)
            .filter(~Task.id.in_(already_done))
            .all()
        )

        saved = 0
        for t in tasks:
            result = prelabel(t.text, project.label_options)
            if result:
                db.session.add(AIPrediction(
                    task_id=t.id,
                    model_name=result["model"],
                    label=result["label"],
                    confidence=result["confidence"]
                ))
                db.session.commit()
                saved += 1
            time.sleep(0.5)  ## small pause to respect Groq rate limits

        return "saved " + str(saved) + " of " + str(len(tasks))