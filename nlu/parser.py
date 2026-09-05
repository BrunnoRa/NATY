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
    value = re.sub(r"\b(?:às?\s*)?(?:uma|duas|três|tres|quatro|cinco|seis|sete|oito|nove|dez|onze|doze)\b", "", value, flags=re.I)
    return re.sub(r"\s+", " ", value).strip(" .,;:-")


class RuleParser:
    def parse(self, text: str) -> Intent:
        raw, clean, plain = text, text.strip(), _plain(text.strip())
        if not clean: return Intent(intents.UNKNOWN, raw_text=raw)
        if re.search(r"\b(?:me (?:da|de) (?:meu )?briefing|briefing do dia|como esta meu dia)\b", plain) or re.fullmatch(r"bom dia naty[!. ]*", plain):
            return Intent(intents.DAILY_BRIEFING, raw_text=raw)
        if re.fullmatch(r"(?:oi|ola|bom dia|boa tarde|boa noite)(?:\s+naty)?[!. ]*", plain):
            return Intent(intents.CHAT, {"kind": "greeting"}, raw_text=raw)
        if re.search(r"\b(que horas sao|qual (?:e )?a hora|hora agora)\b", plain):
            return Intent(intents.TIME_QUERY, raw_text=raw)
        if re.search(r"\b(?:meu (?:pc|computador)|computador|pc)\b.*\b(?:lento|travando|diagnostico)\b|\bpor que.*\b(?:pc|computador).*\blento\b", plain):
            return Intent(intents.SYSTEM_DIAGNOSIS, {"focus": "diagnosis"}, raw_text=raw)
        if re.search(r"\bquanto (?:a )?naty (?:esta )?(?:consumindo|usando)\b|\bconsumo da naty\b", plain):
            return Intent(intents.SYSTEM_STATUS, {"focus": "naty"}, raw_text=raw)
        if re.search(r"\b(?:o que|qual processo).*\b(?:mais ram|mais memoria)\b|\busando mais (?:ram|memoria)\b", plain):
            return Intent(intents.SYSTEM_STATUS, {"focus": "top_memory"}, raw_text=raw)
        if re.search(r"\bquanto (?:de )?(?:ram|memoria).*(?:usando|uso|disponivel)\b|\buso de (?:ram|memoria)\b", plain):
            return Intent(intents.SYSTEM_STATUS, {"focus": "memory"}, raw_text=raw)
        if re.search(r"\bcomo (?:esta|vai).*(?:meu )?(?:pc|computador)\b|\bestado (?:do|deste) (?:pc|computador)\b", plain):
            return Intent(intents.SYSTEM_STATUS, {"focus": "general"}, raw_text=raw)
        if re.search(r"\b(?:onde paramos|onde eu parei|retoma o contexto)\b", plain):
            return Intent(intents.TEMPORAL_RECALL, {"kind": "where_stopped"}, raw_text=raw)
        if re.search(r"\b(?:o que (?:eu )?fiz|minha atividade) hoje\b", plain):
            return Intent(intents.TEMPORAL_RECALL, {"kind": "today"}, raw_text=raw)
        if re.search(r"\b(?:o que (?:eu )?fiz|minha atividade) ontem\b|\bo que estava fazendo ontem\b", plain):
            return Intent(intents.TEMPORAL_RECALL, {"kind": "yesterday"}, raw_text=raw)
        if re.search(r"\b(?:qual foi )?minha ultima pesquisa\b", plain):
            return Intent(intents.TEMPORAL_RECALL, {"kind": "last_research"}, raw_text=raw)
        if re.search(r"\b(?:qual foi )?minha ultima decisao(?: sobre a naty)?\b", plain):
            return Intent(intents.TEMPORAL_RECALL, {"kind": "last_decision"}, raw_text=raw)
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
        if re.search(r"\b(estou|estarei|vou estar)\s+livre\b", plain):
            return Intent(intents.GOOGLE_CALENDAR_FREE, {"starts_at": parse_datetime(clean)}, raw_text=raw)
        if re.search(r"\b(apaga|exclui|remove)\s+(todas\s+)?as\s+tarefas\b", plain): return Intent(intents.DELETE_ALL_TASKS, raw_text=raw)
        if re.search(r"\b(?:salva|salve)\b.*\bpesquisa\b.*\bobsidian\b", plain): return Intent(intents.SAVE_RESEARCH, raw_text=raw)
        if re.search(r"\b(?:abre|abrir)\b.*\bpesquisa\b.*\bnavegador\b", plain): return Intent(intents.OPEN_RESEARCH_BROWSER, raw_text=raw)
        if re.search(r"^coloca\s+isso\s+para\b", plain) and parse_datetime(clean): return Intent(intents.POSTPONE_LAST, {"due_at": parse_datetime(clean)}, raw_text=raw)
        if re.search(r"\bo que (?:voce )?lembra (?:sobre mim|de mim)\b", plain): return Intent(intents.UNKNOWN, raw_text=raw)

        if re.search(r"\b(?:analise|pensar|pense|reflexao)\b.*\b(?:profunda|profundamente|carreira)\b", plain):
            return Intent(intents.DELEGATE, {"query": clean}, raw_text=raw)
        if re.search(r"\bo que (?:voce )?sabe (?:sobre|do|da)\b", plain):
            query = re.sub(r"^.*?\bsabe\s+(?:sobre|do|da)\s+", "", clean, flags=re.I).strip(" ?.!")
            return Intent(intents.OBSIDIAN_QUERY, {"query": query}, raw_text=raw)
        open_app = re.search(r"\b(?:abre|abra|abrir)\s+(?:o\s+|a\s+)?(spotify|musica|player|obsidian|youtube|chatgpt|gmail)\b", plain)
        if open_app:
            app = "spotify" if open_app.group(1) in {"musica", "player"} else open_app.group(1)
            return Intent(intents.OPEN_APP, {"app": app}, raw_text=raw)
        media_actions = {
            "proxima musica": "next", "proxima faixa": "next", "avanca musica": "next",
            "musica anterior": "previous", "faixa anterior": "previous",
            "pausa": "pause", "pause": "pause", "toca": "play", "continue a musica": "play",
            "aumenta o volume": "volume_up", "abaixa o volume": "volume_down", "diminui o volume": "volume_down",
        }
        for phrase, action in media_actions.items():
            if phrase in plain:
                return Intent(intents.MEDIA_CONTROL, {"action": action}, raw_text=raw)

        recurring = re.search(r"\b(todo dia|todos os dias|tod[oa]\s+(segunda|terca|quarta|quinta|sexta|sabado|domingo)(?:-feira)?)\b", plain)
        if recurring and "lembra" in plain:
            when = parse_datetime(clean)
            body = re.sub(r"^.*?\bme\s+lembra(?:-me)?\s+(?:de\s+)?", "", clean, flags=re.I).strip()
            body = _strip_datetime_words(body)
            frequency = "DAILY" if recurring.group(1) in {"todo dia", "todos os dias"} else "WEEKLY"
            return Intent(intents.CREATE_AUTOMATION, {"text": body, "frequency": frequency, "next_run": when}, raw_text=raw)
        if re.search(r"\bdaqui\s+a\s+(?:\d+|uma|duas|tres|quatro|cinco|seis)\s+horas?\b", plain) and "lembra" in plain:
            body = re.sub(r"^.*?\bme\s+lembra(?:-me)?\s+(?:de\s+)?", "", clean, flags=re.I).strip()
            return Intent(intents.CREATE_AUTOMATION, {"text": _strip_datetime_words(body), "frequency": "ONE_TIME", "next_run": parse_datetime(clean)}, raw_text=raw)

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
        task_add = re.search(r"^(?:adiciona|adicione|coloca|coloque)\s+(.+)$", clean, re.I)
        if task_add and parse_datetime(task_add.group(1)) and not re.search(r"\b(?:lista|compras?)\b", plain):
            body = task_add.group(1).strip()
            return Intent(intents.CREATE_TASK, {"title": _strip_datetime_words(body), "due_at": parse_datetime(body), "estimated_minutes": parse_minutes(body)}, raw_text=raw)
        m = re.search(r"^(?:adiciona|adicione|coloca|coloque)\s+(.+)$", clean, re.I)
        if m and not re.search(r"\b(tarefa|lembrete|prioridade)\b", plain):
            item_text, list_name = m.group(1), None
            if re.search(r"\s+(?:na|para a)\s+(?:minha\s+)?lista\s*$", item_text, re.I):
                item_text = re.sub(r"\s+(?:na|para a)\s+(?:minha\s+)?lista\s*$", "", item_text, flags=re.I)
                list_name = "Lista de Compras"
            target = re.search(r"\s+(?:na|no|para a|para o)\s+(?:lista\s+(?:de|da)\s+)([\wà-ÿ ]+)$", item_text, re.I)
            if target:
                list_name = target.group(1); item_text = item_text[:target.start()]
            return Intent(intents.ADD_LIST_ITEMS, {"items": split_items(item_text), "list_name": normalize_list_name(list_name) if list_name else None}, raw_text=raw)
        m = re.search(r"^(?:tira|retira|remove|remova)\s+(.+)$", clean, re.I)
        if m:
            item, list_name = m.group(1), None
            target = re.search(r"\s+(?:da|de)\s+(?:lista\s+(?:de|da)\s+)?([\wà-ÿ ]+)$", item, re.I)
            if target: list_name, item = target.group(1), item[:target.start()]
            return Intent(intents.REMOVE_LIST_ITEM, {"item": item.strip(), "list_name": normalize_list_name(list_name) if list_name else None}, raw_text=raw)
        m = re.search(r"^(?:marca|marque)\s+(.+?)\s+como\s+(?:comprado|comprada)", clean, re.I)
        if m: return Intent(intents.CHECK_LIST_ITEM, {"item": m.group(1).strip(), "list_name": None}, raw_text=raw)
        if re.search(r"\b(limpa|remova?)\b.*\b(comprados|concluidos|marcados)\b", plain): return Intent(intents.CLEAR_CHECKED, {"list_name": None}, raw_text=raw)
        if re.search(r"\b(o que falta comprar|abre? (?:a |minha )?lista|mostra? (?:a |minha )?lista|lista de compras)\b", plain):
            name_match = re.search(r"lista\s+(?:de|da)\s+([\wà-ÿ ]+)", clean, re.I)
            name = normalize_list_name(name_match.group(1)) if name_match else ("Lista de Compras" if "compr" in plain else None)
            return Intent(intents.SHOW_LIST, {"list_name": name, "unchecked_only": "falta" in plain}, raw_text=raw)

        minutes = parse_minutes(clean)
        if minutes is not None and re.search(r"\b(tenho|disponivel|consigo fazer)\b", plain): return Intent(intents.PLAN_TIME, {"minutes": minutes}, raw_text=raw)
        if re.search(r"\b(o que faco agora|o que fazer agora|qual (?:e )?a minha proxima tarefa)\b", plain): return Intent(intents.NEXT_TASK, raw_text=raw)
        if re.search(r"\b(o que (?:eu )?tenho (?:hoje|amanha)|mostra (?:o |meu )?dia|meu dia)\b", plain):
            return Intent(intents.SHOW_DAY, {"day": "tomorrow" if "amanha" in plain else "today"}, raw_text=raw)
        if re.search(r"\b(compromissos|agenda de hoje|o que tenho na agenda)\b", plain): return Intent(intents.LIST_APPOINTMENTS, raw_text=raw)
        if re.search(r"\b(o que (?:eu )?tenho para fazer|tarefas? (?:de )?hoje|minhas tarefas|pendencias|ficou pendente)\b", plain): return Intent(intents.LIST_TASKS, raw_text=raw)
        if re.search(r"\b(terminei|conclui|feito)\b", plain) and len(plain.split()) <= 5: return Intent(intents.COMPLETE_LAST, raw_text=raw)
        complete = re.search(r"^(?:marca|marque)\s+(.+?)\s+como\s+(?:concluída|concluído|concluida|concluido|feita|feito)$", clean, re.I)
        if complete: return Intent(intents.COMPLETE_TASK, {"query": complete.group(1).strip()}, raw_text=raw)
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
