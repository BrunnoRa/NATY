from __future__ import annotations

import unittest

from delegation.external_ai import ChatGPTWebProvider, ExternalResultImporter
from knowledge.context import ContextNote, ContextPack
from learning.manager import LearningManager


class Retriever:
    def retrieve(self, query):
        return ContextPack(query, [ContextNote("Projeto", "03 - Projetos/NATY.md",
                           "A NATY é local. api_key=segredo-que-nao-pode-sair")],
                           {"project": {"name": "NATY"}}, 1000)


class Memories:
    def __init__(self): self.saved = []
    def set(self, *args): self.saved.append(args)


class Obsidian:
    def __init__(self): self.entries = []
    def append_evolution(self, entry): self.entries.append(entry)


class DelegationLearningTests(unittest.TestCase):
    def test_delegation_uses_relevant_context_and_redacts_secrets(self):
        copied, opened = [], []
        result = ChatGPTWebProvider(Retriever(), copied.append, opened.append).prepare("Devo focar em Java?")
        self.assertTrue(result.ok)
        self.assertEqual(opened, ["https://chatgpt.com/"])
        self.assertIn("# Contexto preparado pela NATY", copied[0])
        self.assertIn("Projeto relacionado:\nNATY", copied[0])
        self.assertNotIn("segredo-que-nao-pode-sair", copied[0])

    def test_external_result_is_structured_before_saving(self):
        result = ExternalResultImporter().result(
            "Decisão: focar em segurança.\nPróximo passo: concluir o curso.\nFonte https://example.com")
        self.assertTrue(result.ok)
        self.assertEqual(len(result.data["decisions"]), 1)
        self.assertEqual(len(result.data["tasks"]), 1)
        self.assertEqual(result.data["links"], ["https://example.com"])
        self.assertIn("Deseja salvá-las", result.message)

    def test_learning_requires_confirmation_and_logs_evolution(self):
        memories, obsidian = Memories(), Obsidian()
        manager = LearningManager(memories, obsidian)
        proposal = manager.propose(manager.detect("Prefiro que você fale mais curto pela manhã."))
        self.assertFalse(proposal.ok)
        self.assertEqual(memories.saved, [])
        saved = manager.confirm()
        self.assertTrue(saved.ok)
        self.assertEqual(memories.saved[0][0], "NEW_PREFERENCE")
        self.assertTrue(obsidian.entries[0]["confirmado"])

    def test_learning_cancel_does_not_persist(self):
        memories = Memories(); manager = LearningManager(memories)
        manager.propose(manager.detect("Eu decidi estudar segurança."))
        manager.cancel()
        self.assertEqual(memories.saved, [])


if __name__ == "__main__": unittest.main()
