from datetime import datetime, timezone
import unittest

from nlu import intents
from nlu.date_parser import parse_datetime
from nlu.parser import RuleParser


class DateParserTests(unittest.TestCase):
    def setUp(self): self.base = datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc)

    def test_tomorrow_time(self): self.assertEqual(parse_datetime("amanhã às 15h", self.base), "2026-09-05T15:00+00:00")
    def test_weekday(self): self.assertEqual(parse_datetime("sexta", self.base), "2026-09-11T09:00+00:00")
    def test_numeric_date(self): self.assertEqual(parse_datetime("dia 10/09 às 8:30", self.base), "2026-09-10T08:30+00:00")
    def test_invalid_time(self): self.assertIsNone(parse_datetime("amanhã às 28h", self.base))


class ParserTests(unittest.TestCase):
    def setUp(self): self.parser = RuleParser()

    def test_add_multiple_items(self):
        parsed = self.parser.parse("adiciona café, arroz e leite na lista de compras")
        self.assertEqual(parsed.name, intents.ADD_LIST_ITEMS); self.assertEqual(parsed.entities["items"], ["café", "arroz", "leite"])
        self.assertEqual(parsed.entities["list_name"], "Lista de Compras")

    def test_contextual_add(self):
        parsed = self.parser.parse("adiciona carregador e escova")
        self.assertEqual(parsed.name, intents.ADD_LIST_ITEMS); self.assertIsNone(parsed.entities["list_name"])

    def test_reminder(self):
        parsed = self.parser.parse("me lembra amanhã às 14h de ligar para João")
        self.assertEqual(parsed.name, intents.CREATE_REMINDER); self.assertEqual(parsed.entities["text"], "ligar para João")

    def test_task(self):
        parsed = self.parser.parse("cria tarefa entregar relatório sexta")
        self.assertEqual(parsed.name, intents.CREATE_TASK); self.assertEqual(parsed.entities["title"], "entregar relatório")

    def test_research(self): self.assertEqual(self.parser.parse("pesquisa monitor até 900 reais").name, intents.RESEARCH)
    def test_compare(self): self.assertEqual(self.parser.parse("compara RX 7600 com RTX 4060").name, intents.COMPARE)
    def test_plan(self): self.assertEqual(self.parser.parse("tenho 10 minutos").entities["minutes"], 10)
    def test_destructive_requires_intent(self): self.assertEqual(self.parser.parse("apaga todas as tarefas").name, intents.DELETE_ALL_TASKS)
    def test_appointment(self): self.assertEqual(self.parser.parse("agenda dentista amanhã às 10h").name, intents.CREATE_APPOINTMENT)
    def test_remove_item_target(self):
        parsed = self.parser.parse("tira café da lista de compras")
        self.assertEqual(parsed.entities, {"item": "café", "list_name": "Lista de Compras"})
    def test_pending_yesterday(self): self.assertEqual(self.parser.parse("o que ficou pendente de ontem?").name, intents.LIST_TASKS)
    def test_contextual_reschedule(self): self.assertEqual(self.parser.parse("coloca isso para semana que vem").name, intents.POSTPONE_LAST)
    def test_project_overdue(self):
        parsed = self.parser.parse("quais tarefas do TCC estão atrasadas?")
        self.assertEqual(parsed.name, intents.PROJECT_OVERDUE); self.assertEqual(parsed.entities["name"], "tcc")
