from __future__ import annotations

import re
import unicodedata

from core.models import Intent
from nlu import intents
from nlu.date_parser import parse_datetime
from nlu.entities import normalize_list_name, parse_minutes, split_items


def _plain(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")


def _strip_datetime_words(text: str) -> str:
    value = re.sub(r"\b(?:hoje|amanhã|depois de amanhã|semana que vem|próxima semana)\b", "", text, flags=re.I)
    value = re.sub(r"\b(?:segunda|terça|quarta|quinta|sexta|sábado|domingo)(?:-feira)?\b", "", value, flags=re.I)
    value = re.sub(r"\b(?:às?\s*)?\d{1,2}(?::\d{2}|h\d{0,2}|\s+horas?)\b", "", value, flags=re.I)
    return re.sub(r"\s+", " ", value).strip(" .,;:-")


class RuleParser:
    def parse(self, text: str) -> Intent:
        raw, clean, plain = text, text.strip(), _plain(text.strip())
        if not clean: return Intent(intents.UNKNOWN, raw_text=raw)
        if plain in {"sim", "confirmo", "pode", "pode fazer"}: return Intent(intents.CONFIRM, raw_text=raw)
        if plain in {"nao", "cancelar", "cancela"}: return Intent(intents.CANCEL, raw_text=raw)
        if re.search(r"\b(ajuda|comandos|o que voce faz)\b", plain): return Intent(intents.HELP, raw_text=raw)
        if re.search(r"\b(desconecta|desconectar|remove|remover)\b.*\bgoogle\b", plain): return Intent(intents.DISCONNECT_GOOGLE, raw_text=raw)
        if re.search(r"\b(conecta|conectar|autoriza|autorizar)\b.*\bgoogle\b", plain): return Intent(intents.CONNECT_GOOGLE, raw_text=raw)
        if re.search(r"\b(envia|enviar|mande|mandar)\b.*\brascunho\b", plain): return Intent(intents.GMAIL_SEND, raw_text=raw)
        draft = re.search(r"\b(?:cria|crie|prepare|faz|faca)\s+(?:um\s+)?rascunho(?:\s+de\s+e-?mail)?\s+para\s+([^\s,;]+)(?:\s+assunto\s+(.+?))?(?:\s+mensagem\s+(.+))?$", clean, re.I)
        if draft:
            return Intent(intents.GMAIL_DRAFT, {"to": draft.group(1), "subject": (draft.group(2) or "Mensagem da Naty").strip(), "body": (draft.group(3) or "").strip()}, raw_text=raw)
        if re.search(r"\b(e-?mails?|gmail|caixa de entrada)\b", plain) and re.search(r"\b(mostra|liste|lista|procura|busca|nao lidos?)\b", plain):
            query = "is:unread" if "nao lido" in plain else re.sub(r"^.*?\b(?:sobre|de)\b", "", clean, flags=re.I).strip()
            return Intent(intents.GMAIL_SEARCH, {"query": query or "in:inbox"}, raw_text=raw)
        if re.search(r"\b(agenda|calendario)\b.*\bgoogle\b", plain): return Intent(intents.GOOGLE_CALENDAR_UPCOMING, raw_text=raw)
        if re.search(r"\b(apaga|exclui|remove)\s+(todas\s+)?as\s+tarefas\b", plain): return Intent(intents.DELETE_ALL_TASKS, raw_text=raw)
        if re.search(r"\b(?:salva|salve)\b.*\bpesquisa\b.*\bobsidian\b", plain): return Intent(intents.SAVE_RESEARCH, raw_text=raw)
        if re.search(r"\b(?:abre|abrir)\b.*\bpesquisa\b.*\bnavegador\b", plain): return Intent(intents.OPEN_RESEARCH_BROWSER, raw_text=raw)
        if re.search(r"^coloca\s+isso\s+para\b", plain) and parse_datetime(clean): return Intent(intents.POSTPONE_LAST, {"due_at": parse_datetime(clean)}, raw_text=raw)
        if re.search(r"\bo que (?:voce )?lembra (?:sobre mim|de mim)\b", plain): return Intent(intents.UNKNOWN, raw_text=raw)

        m = re.search(r"\b(?:me\s+)?lembra(?:-me)?\s+(?:de\s+)?(.+)", clean, re.I)
        if m:
            body = m.group(1).strip()
            when = parse_datetime(body)
            reminder_text = _strip_datetime_words(body)
            reminder_text = re.sub(r"^(?:de\s+)", "", reminder_text, flags=re.I)
            return Intent(intents.CREATE_REMINDER, {"text": reminder_text, "remind_at": when}, raw_text=raw)

        if re.search(r"\b(compara|compare)\b", plain):
            query = re.sub(r"^.*?\b(?:compara|compare)\b", "", clean, flags=re.I).strip()
            return Intent(intents.COMPARE, {"query": query}, raw_text=raw)
        if re.search(r"\b(pesquisa|pesquise|procura|procure)\b", plain):
            query = re.sub(r"^.*?\b(?:pesquisa|pesquise|procura|procure)\b", "", clean, flags=re.I).strip(" :")
            return Intent(intents.RESEARCH, {"query": query}, raw_text=raw)

        if re.search(r"\b(?:cria|crie)\s+(?:uma\s+)?lista\b", plain):
            name = re.sub(r"^.*?\blista\s*(?:chamada|de|da)?\s*", "", clean, flags=re.I).strip(" .")
            return Intent(intents.CREATE_LIST, {"name": normalize_list_name(name)}, raw_text=raw)
        m = re.search(r"^(?:adiciona|adicione|coloca|coloque)\s+(.+)$", clean, re.I)
        if m and not re.search(r"\b(tarefa|lembrete|prioridade)\b", plain):
            item_text, list_name = m.group(1), None
            target = re.search(r"\s+(?:na|no|para a|para o)\s+(?:lista\s+(?:de|da)\s+)?([\wà-ÿ ]+)$", item_text, re.I)
            if target:
                list_name = target.group(1); item_text = item_text[:target.start()]
            return Intent(intents.ADD_LIST_ITEMS, {"items": split_items(item_text), "list_name": normalize_list_name(list_name) if list_name else None}, raw_text=raw)
        m = re.search(r"^(?:tira|retira|remove|remova)\s+(.+)$", clean, re.I)
        if m:
            item, list_name = m.group(1), None
            target = re.search(r"\s+(?:da|de)\s+(?:lista\s+(?:de|da)\s+)?([\wà-ÿ ]+)$", item, re.I)
            if target: list_name, item = target.group(1), item[:target.start()]
            return Intent(intents.REMOVE_LIST_ITEM, {"item": item.strip(), "list_name": normalize_list_name(list_name) if list_name else None}, raw_text=raw)
        m = re.search(r"^(?:marca|marque)\s+(.+?)\s+como\s+(?:comprado|comprada|feito|concluído|concluida)", clean, re.I)
        if m: return Intent(intents.CHECK_LIST_ITEM, {"item": m.group(1).strip(), "list_name": None}, raw_text=raw)
        if re.search(r"\b(limpa|remova?)\b.*\b(comprados|concluidos|marcados)\b", plain): return Intent(intents.CLEAR_CHECKED, {"list_name": None}, raw_text=raw)
        if re.search(r"\b(o que falta comprar|abre? (?:a |minha )?lista|mostra? (?:a |minha )?lista|lista de compras)\b", plain):
            name_match = re.search(r"lista\s+(?:de|da)\s+([\wà-ÿ ]+)", clean, re.I)
            name = normalize_list_name(name_match.group(1)) if name_match else ("Lista de Compras" if "compr" in plain else None)
            return Intent(intents.SHOW_LIST, {"list_name": name, "unchecked_only": "falta" in plain}, raw_text=raw)

        minutes = parse_minutes(clean)
        if minutes is not None and re.search(r"\b(tenho|disponivel|consigo fazer)\b", plain): return Intent(intents.PLAN_TIME, {"minutes": minutes}, raw_text=raw)
        if re.search(r"\b(o que faco agora|o que fazer agora)\b", plain): return Intent(intents.PLAN_NOW, raw_text=raw)
        if re.search(r"\b(compromissos|agenda de hoje|o que tenho na agenda)\b", plain): return Intent(intents.LIST_APPOINTMENTS, raw_text=raw)
        if re.search(r"\b(o que (?:eu )?tenho para fazer|tarefas? (?:de )?hoje|minhas tarefas|pendencias|ficou pendente)\b", plain): return Intent(intents.LIST_TASKS, raw_text=raw)
        if re.search(r"\b(terminei|conclui|feito)\b", plain) and len(plain.split()) <= 5: return Intent(intents.COMPLETE_LAST, raw_text=raw)
        if re.search(r"\b(prioridade alta|como prioridade alta)\b", plain): return Intent(intents.UPDATE_LAST, {"priority": "high"}, raw_text=raw)
        if re.search(r"\b(nao fiz|adia|adie|remarca|remarque)\b", plain): return Intent(intents.POSTPONE_LAST, {"due_at": parse_datetime(clean)}, raw_text=raw)

        m = re.search(r"^(?:cria|crie|nova)?\s*tarefa\s+(.+)$", clean, re.I)
        if not m and re.search(r"^(?:tenho que|preciso)\s+", clean, re.I): m = re.search(r"^(?:tenho que|preciso)\s+(.+)$", clean, re.I)
        if m:
            body = m.group(1).strip()
            return Intent(intents.CREATE_TASK, {"title": _strip_datetime_words(body), "due_at": parse_datetime(body), "estimated_minutes": parse_minutes(body)}, raw_text=raw)
        m = re.search(r"^(?:agenda|marque|marca|cria compromisso)\s+(.+)$", clean, re.I)
        if m:
            body = m.group(1).strip()
            return Intent(intents.CREATE_APPOINTMENT, {"title": _strip_datetime_words(body), "starts_at": parse_datetime(body)}, raw_text=raw)
        m = re.search(r"^(?:cria|crie)\s+(?:um\s+)?projeto\s+(.+)$", clean, re.I)
        if m: return Intent(intents.CREATE_PROJECT, {"name": m.group(1).strip(" .")}, raw_text=raw)
        m = re.search(r"(?:quais\s+)?tarefas\s+(?:do|da)\s+(.+?)\s+(?:estao\s+)?atrasadas", plain, re.I)
        if m: return Intent(intents.PROJECT_OVERDUE, {"name": m.group(1).strip()}, raw_text=raw)
        m = re.search(r"(?:anota|anote)\s+(.+?)(?:\s+no\s+projeto\s+(.+))?$", clean, re.I)
        if m: return Intent(intents.CREATE_NOTE, {"content": m.group(1).strip(), "project": m.group(2)}, raw_text=raw)
        return Intent(intents.UNKNOWN, confidence=0.0, raw_text=raw)
