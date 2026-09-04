import sys
import types
from unittest.mock import patch

from ai.llama_cpp import LlamaCppProvider
from tests.base import TempDatabaseTest


class AIV2Tests(TempDatabaseTest):
    def test_load_generate_and_unload(self):
        model_path = self.root / "tiny.gguf"; model_path.write_bytes(b"gguf")

        class FakeLlama:
            def __init__(self, **kwargs): self.kwargs = kwargs
            def __call__(self, prompt, **kwargs): return {"choices": [{"text": " resposta "}]}

        provider = LlamaCppProvider(str(model_path), idle_unload_seconds=999, max_ram_mb=10, min_available_ram_mb=1)
        with patch.dict(sys.modules, {"llama_cpp": types.SimpleNamespace(Llama=FakeLlama)}), patch.object(provider, "available_ram_mb", return_value=4096):
            self.assertEqual(provider.generate("oi"), "resposta")
            self.assertTrue(provider.loaded)
            provider.unload()
            self.assertFalse(provider.loaded)

    def test_model_size_guard(self):
        model_path = self.root / "large.gguf"; model_path.write_bytes(b"x" * 2048)
        provider = LlamaCppProvider(str(model_path), max_ram_mb=0.001, min_available_ram_mb=0)
        with patch.object(provider, "is_available", return_value=True):
            with self.assertRaisesRegex(RuntimeError, "limite de memória"):
                provider.load()
