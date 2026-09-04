from types import SimpleNamespace

from core.models import AppState
from downloads.manager import DownloadManager, DownloadSpec
from nlu import intents
from nlu.parser import RuleParser
from scheduler.scheduler import Scheduler
from database.repositories.reminders import ReminderRepository
from database.repositories.tasks import TaskRepository
from tests.base import TempDatabaseTest
from ui.state_indicator import COLORS


class V2BoundaryTests(TempDatabaseTest):
    def test_google_intents_and_send_are_separate(self):
        parser = RuleParser()
        self.assertEqual(parser.parse("conectar Google").name, intents.CONNECT_GOOGLE)
        self.assertEqual(parser.parse("desconectar Google").name, intents.DISCONNECT_GOOGLE)
        self.assertEqual(parser.parse("mostra emails não lidos").name, intents.GMAIL_SEARCH)
        draft = parser.parse("cria rascunho de email para ana@example.com assunto Oi mensagem Tudo bem?")
        self.assertEqual(draft.name, intents.GMAIL_DRAFT)
        self.assertEqual(draft.entities["to"], "ana@example.com")
        self.assertEqual(parser.parse("enviar rascunho").name, intents.GMAIL_SEND)

    def test_daily_briefing_runs_once(self):
        notifications = []
        settings = SimpleNamespace(
            proactivity_enabled=True, overdue_followup=False,
            morning_briefing=True, evening_review=False,
            morning_briefing_time="00:00", evening_review_time="23:59",
        )
        scheduler = Scheduler(ReminderRepository(self.db), TaskRepository(self.db), lambda title, message: notifications.append((title, message)), settings=settings)
        scheduler.check_once(); scheduler.check_once()
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0][0], "Bom dia")

    def test_proactivity_opt_out_does_not_prompt_overdue(self):
        tasks = TaskRepository(self.db); tasks.create("Atrasada", due_at="2020-01-01T00:00:00-03:00")
        settings = SimpleNamespace(proactivity_enabled=False, overdue_followup=True, morning_briefing=False, evening_review=False)
        notifications = []
        Scheduler(ReminderRepository(self.db), tasks, lambda *args: notifications.append(args), settings=settings).check_once()
        self.assertEqual(notifications, [])

    def test_download_allowlist_and_checksum_validation(self):
        manager = DownloadManager()
        with self.assertRaises(ValueError): manager.validate(DownloadSpec("x", "http://example.com/x", 1, "MIT"))
        with self.assertRaises(ValueError): manager.validate(DownloadSpec("x", "https://github.com/x", 1, "MIT", "bad"))

    def test_all_operational_states_have_visual_color(self):
        for state in AppState:
            self.assertIn(state.value, COLORS)
