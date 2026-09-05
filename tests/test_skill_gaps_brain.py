from core.assistant import NatyAssistant
from core.models import ToolResult
from ipc.handler import CoreRequestHandler
from nlu import intents
from tests.base import TempDatabaseTest


class SkillGapBrainTests(TempDatabaseTest):
    def test_unknown_capability_is_saved_only_after_confirmation(self):
        assistant = NatyAssistant(self.settings(), self.db)
        proposal = assistant.handle_result("acompanha minha encomenda espacial")
        self.assertEqual("skill_gap_proposal", proposal.type)
        self.assertEqual(0, self.db.one("SELECT COUNT(*) count FROM skill_gaps")["count"])
        saved = assistant.handle_result("sim")
        self.assertTrue(saved.ok)
        self.assertEqual(1, self.db.one("SELECT COUNT(*) count FROM skill_gaps")["count"])

    def test_skill_gap_can_be_cancelled(self):
        assistant = NatyAssistant(self.settings(), self.db)
        assistant.handle_result("teletransporte meu café")
        assistant.handle_result("não")
        self.assertEqual(0, self.db.one("SELECT COUNT(*) count FROM skill_gaps")["count"])

    def test_brain_terms_come_from_executed_skill(self):
        result = ToolResult(True, "ok", {})
        from core.agent_router import AgentRouter
        decorated = AgentRouter._decorate(result, intents.SYSTEM_STATUS)
        self.assertIn("Sistema", CoreRequestHandler._active_terms(decorated.data))
