from datetime import datetime, timedelta

from database.repositories.lists import ListRepository, slugify
from database.repositories.projects import ProjectRepository
from database.repositories.reminders import ReminderRepository
from database.repositories.tasks import TaskRepository
from tests.base import TempDatabaseTest


class RepositoryTests(TempDatabaseTest):
    def test_task_create_complete(self):
        repo = TaskRepository(self.db); task = repo.create("Relatório", priority="high", estimated_minutes=20)
        self.assertEqual(task["status"], "pending"); self.assertEqual(repo.complete(task["id"])["status"], "completed")

    def test_task_postpone_counts(self):
        repo = TaskRepository(self.db); task = repo.create("Relatório")
        updated = repo.postpone(task["id"], "2030-01-01T09:00")
        self.assertEqual(updated["postpone_count"], 1)

    def test_project_tasks(self):
        projects, tasks = ProjectRepository(self.db), TaskRepository(self.db)
        project = projects.create("TCC"); tasks.create("Revisar", project_id=project["id"])
        self.assertEqual(projects.tasks(project["id"])[0]["title"], "Revisar")

    def test_list_lifecycle(self):
        repo = ListRepository(self.db); shopping = repo.create("Lista de Compras")
        repo.add_item(shopping["id"], "Café"); repo.add_item(shopping["id"], "Leite")
        self.assertEqual(len(repo.items(shopping["id"], False)), 2)
        self.assertTrue(repo.check(shopping["id"], "café")["checked"])
        self.assertEqual(repo.clear_checked(shopping["id"]), 1)
        self.assertEqual([i["text"] for i in repo.items(shopping["id"])], ["Leite"])

    def test_list_does_not_duplicate_unchecked_item(self):
        repo = ListRepository(self.db); record = repo.create("Viagem")
        repo.add_item(record["id"], "Escova"); repo.add_item(record["id"], "escova")
        self.assertEqual(len(repo.items(record["id"])), 1)

    def test_slug_accents(self): self.assertEqual(slugify("Coisas para Viagem"), "coisas-para-viagem")

    def test_reminders_due(self):
        repo = ReminderRepository(self.db)
        past = (datetime.now().astimezone() - timedelta(minutes=1)).isoformat()
        reminder = repo.create("Ligar", past)
        self.assertEqual(repo.due()[0]["id"], reminder["id"])
        repo.mark_triggered(reminder["id"]); self.assertEqual(repo.due(), [])
