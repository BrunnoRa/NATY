from pathlib import Path
import tempfile
import unittest

from core.context import SessionContext
from nlu import intents
from nlu.parser import RuleParser
from tools.clipboard import ClipboardTool
from tools.safe_files import SafeFileAssistant


class FakeClipboard:
    def __init__(self, value): self.value = value; self.reads = 0
    def read(self): self.reads += 1; return self.value


class ClipboardFileTests(unittest.TestCase):
    def test_clipboard_reads_only_when_called_and_handles_empty_text(self):
        provider = FakeClipboard("  texto copiado  ")
        tool = ClipboardTool(provider)
        self.assertEqual(0, provider.reads)
        self.assertTrue(tool.show().ok)
        self.assertEqual(1, provider.reads)
        self.assertFalse(ClipboardTool(FakeClipboard(" ")).show().ok)

    def test_clipboard_summary_is_local_and_bounded(self):
        source = "Primeira frase. Segunda frase! Terceira frase? Quarta frase."
        result = ClipboardTool(FakeClipboard(source)).summarize()
        self.assertTrue(result.ok)
        self.assertNotIn("Quarta frase", result.data["summary"])

    def test_safe_file_search_open_and_root_boundary(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); target = root / "relatorio.txt"; target.write_text("ok", encoding="utf-8")
            opened = []
            context = SessionContext()
            tool = SafeFileAssistant(str(root), opener=opened.append, context=context)
            result = tool.find("relatorio")
            self.assertTrue(result.ok)
            self.assertEqual(str(target), context.state["last_file"])
            self.assertTrue(tool.open_last().ok)
            self.assertEqual(str(target), opened[0])
            outside = root.parent / "outside-naty-test.txt"
            outside.write_text("no", encoding="utf-8")
            try: self.assertFalse(tool.find(str(outside)).ok)
            finally: outside.unlink()

    def test_delete_requires_confirmation_and_recycles_only_after_confirmed_call(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "old.txt"; target.write_text("old", encoding="utf-8")
            recycled = []
            tool = SafeFileAssistant(temp, recycler=recycled.append)
            request = tool.request_delete(str(target))
            self.assertFalse(request.ok)
            self.assertTrue(request.data["requires_confirmation"])
            self.assertEqual([], recycled)
            self.assertTrue(tool.recycle_confirmed(request.data["path"]).ok)
            self.assertEqual([target], recycled)

    def test_parser_routes_clipboard_and_file_commands(self):
        parser = RuleParser()
        self.assertEqual(intents.CLIPBOARD_SUMMARIZE, parser.parse("Resume o que está na área de transferência").name)
        self.assertEqual(intents.CLIPBOARD_RESEARCH, parser.parse("Pesquisa isso que eu copiei").name)
        self.assertEqual(intents.FILE_OPEN_FOLDER, parser.parse("Abre minha pasta Downloads").name)
        self.assertEqual(intents.FILE_FIND, parser.parse("Encontra o arquivo notas.txt").name)
        self.assertEqual(intents.FILE_RECENT, parser.parse("Mostra os arquivos recentes do projeto NATY").name)
