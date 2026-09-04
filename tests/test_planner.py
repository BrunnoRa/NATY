from datetime import datetime, timedelta

from database.repositories.tasks import TaskRepository
from planner.planner import Planner
from planner.scoring import task_score
from tests.base import TempDatabaseTest


class PlannerTests(TempDatabaseTest):
    def test_fits_available_time(self):
        repo = TaskRepository(self.db); repo.create("Curta", estimated_minutes=10); repo.create("Longa", estimated_minutes=60)
        result = Planner(repo).suggest(10)
        self.assertEqual([t["title"] for t in result.data], ["Curta"])

    def test_overdue_scores_higher(self):
        now = datetime.now().astimezone()
        overdue = {"priority": "normal", "due_at": (now-timedelta(days=1)).isoformat(), "estimated_minutes": 30, "postpone_count": 0}
        future = {**overdue, "due_at": (now+timedelta(days=20)).isoformat()}
        self.assertGreater(task_score(overdue, now), task_score(future, now))
