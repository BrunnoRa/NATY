"""Main desktop surface for Naty V2."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from activation.hotkey import GlobalHotkey
from core.assistant import NatyAssistant
from core.models import AppState
from core.performance import PerformanceMonitor
from scheduler.scheduler import Scheduler
from ui.knowledge_graph import KnowledgeGraphCanvas
from ui.mini_window import MiniWindow
from ui.onboarding import OnboardingWizard
from ui.state_indicator import StateIndicator
from ui.tray import TrayIcon
from ui.voice_settings import VoiceSettingsWindow
from voice.manager import VoiceSessionManager


class MainWindow:
    BG = "#060d13"
    PANEL = "#0b1720"
    PANEL_ALT = "#0e1e29"
    BORDER = "#173447"
    CYAN = "#55e6ff"
    TEXT = "#e4f4fb"
    MUTED = "#7695a8"

    def __init__(self, assistant: NatyAssistant, use_tray: bool = True):
        self.assistant, self.settings = assistant, assistant.settings
        self.root = tk.Tk()
        self.root.title("Naty · agente pessoal local")
        self.root.geometry("1120x720")
        self.root.minsize(860, 580)
        self.root.configure(bg=self.BG)
        self.root.option_add("*Font", ("Segoe UI", 10))
        self._closing = False
        self._last_state = AppState.IDLE
        self._listening_from_mini = False
        self.performance = PerformanceMonitor()
        self._configure_style()
        self._build()

        self.voice = VoiceSessionManager(self.settings)
        self.mini = MiniWindow(self.root, self.submit_text)
        self.tray = TrayIcon(
            lambda: self.root.after(0, self.show),
            lambda: self.root.after(0, self.listen),
            lambda: self.root.after(0, self.focus_task),
            lambda: self.root.after(0, self.open_shopping_list),
            lambda: self.root.after(0, self.open_settings),
            lambda: self.root.after(0, self.exit),
        )
        if use_tray:
            self.tray.start()
        self.hotkey = GlobalHotkey(
            self.settings.hotkey,
            lambda: self.root.after(0, self.show_mini),
        )
        self.hotkey.start()
        self.scheduler = Scheduler(
            assistant.reminder_repo,
            assistant.task_repo,
            self._notify,
            self.settings.scheduler_interval_seconds,
            self.settings,
        )
        if self.settings.notifications_enabled:
            self.scheduler.start()
        assistant.events.subscribe(
            "state", lambda state: self.root.after(0, self._set_state, state)
        )
        self.root.protocol("WM_DELETE_WINDOW", self.hide if self.tray.running else self.exit)
        self._refresh_dashboard()
        self._performance_tick()
        if not self.settings.first_run_completed:
            self.root.after(250, lambda: OnboardingWizard(self.root, self.assistant, self._refresh_dashboard))

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", background=self.BG, foreground=self.TEXT)
        style.configure("TFrame", background=self.BG)
        style.configure("Panel.TFrame", background=self.PANEL)
        style.configure("TLabel", background=self.BG, foreground=self.TEXT)
        style.configure("Muted.TLabel", background=self.BG, foreground=self.MUTED)
        style.configure("Panel.TLabel", background=self.PANEL, foreground=self.TEXT)
        style.configure(
            "TButton", background=self.PANEL_ALT, foreground=self.TEXT,
            bordercolor=self.BORDER, padding=(10, 6),
        )
        style.map("TButton", background=[("active", "#143243")])
        style.configure(
            "TEntry", fieldbackground=self.PANEL_ALT, foreground=self.TEXT,
            insertcolor=self.CYAN, bordercolor=self.BORDER,
        )
        style.configure("TCheckbutton", background=self.BG, foreground=self.TEXT)
        style.configure(
            "Treeview", background=self.PANEL, fieldbackground=self.PANEL,
            foreground=self.TEXT, bordercolor=self.BORDER,
        )
        style.configure("Treeview.Heading", background=self.PANEL_ALT, foreground=self.CYAN)

    def _build(self) -> None:
        header = ttk.Frame(self.root, padding=(18, 12))
        header.pack(fill="x")
        ttk.Label(header, text="◉  NATY", font=("Segoe UI", 18, "bold"), foreground=self.CYAN).pack(side="left")
        ttk.Label(header, text="LOCAL-FIRST", style="Muted.TLabel", font=("Segoe UI", 8, "bold")).pack(side="left", padx=12)
        self.state = StateIndicator(header, text="● IDLE")
        self.state.pack(side="right")

        body = tk.PanedWindow(
            self.root, orient="horizontal", bg=self.BORDER, sashwidth=1,
            borderwidth=0, relief="flat",
        )
        body.pack(fill="both", expand=True, padx=14)

        left = tk.Frame(body, bg=self.PANEL, width=230)
        center = tk.Frame(body, bg=self.PANEL, width=620)
        right = tk.Frame(body, bg=self.PANEL, width=240)
        body.add(left, minsize=190, width=230)
        body.add(center, minsize=430, stretch="always")
        body.add(right, minsize=190, width=240)
        self._build_left(left)
        self._build_center(center)
        self._build_right(right)

        bottom = ttk.Frame(self.root, padding=(14, 10, 14, 14))
        bottom.pack(fill="x")
        self.entry = ttk.Entry(bottom, font=("Segoe UI", 11))
        self.entry.pack(side="left", fill="x", expand=True, ipady=5)
        self.entry.bind("<Return>", lambda _event: self.send_entry())
        ttk.Button(bottom, text="🎤", width=4, command=self.listen).pack(side="left", padx=(8, 4))
        ttk.Button(bottom, text="Enviar", command=self.send_entry).pack(side="left")
        self._append("naty", "Naty", "Pronta. Seus dados locais e suas decisões continuam sob seu controle.")

    def _panel_title(self, master: tk.Misc, text: str) -> None:
        tk.Label(
            master, text=text, bg=self.PANEL, fg=self.CYAN,
            font=("Segoe UI", 9, "bold"), anchor="w",
        ).pack(fill="x", padx=12, pady=(12, 8))

    def _build_left(self, master: tk.Misc) -> None:
        self._panel_title(master, "HOJE")
        self.today_list = tk.Listbox(
            master, bg=self.PANEL, fg=self.TEXT, selectbackground="#153b4d",
            selectforeground=self.TEXT, relief="flat", highlightthickness=0,
            activestyle="none", font=("Segoe UI", 9),
        )
        self.today_list.pack(fill="both", expand=True, padx=8)
        self.today_list.bind("<Double-Button-1>", self._complete_selected_task)
        actions = tk.Frame(master, bg=self.PANEL)
        actions.pack(fill="x", padx=8, pady=10)
        ttk.Button(actions, text="+ tarefa", command=self.focus_task).pack(fill="x", pady=2)
        ttk.Button(actions, text="lista de compras", command=self.open_shopping_list).pack(fill="x", pady=2)

    def _build_center(self, master: tk.Misc) -> None:
        self.graph = KnowledgeGraphCanvas(master, height=340)
        self.graph.pack(fill="both", expand=True)
        self.history = tk.Text(
            master, height=12, wrap="word", state="disabled", relief="flat",
            padx=14, pady=10, bg="#08131c", fg=self.TEXT,
            insertbackground=self.CYAN, highlightthickness=1,
            highlightbackground=self.BORDER,
        )
        self.history.pack(fill="x")
        self.history.tag_configure("user", foreground="#7fb9ff", spacing1=9, font=("Segoe UI", 9, "bold"))
        self.history.tag_configure("naty", foreground=self.CYAN, spacing1=9, font=("Segoe UI", 9, "bold"))
        self.history.tag_configure("body", foreground=self.TEXT, spacing3=5)

    def _build_right(self, master: tk.Misc) -> None:
        self._panel_title(master, "CONTEXTO")
        self.context_label = tk.Label(
            master, text="Nenhum item em foco", bg=self.PANEL, fg=self.TEXT,
            justify="left", anchor="nw", wraplength=205,
        )
        self.context_label.pack(fill="x", padx=12)
        self._panel_title(master, "MÓDULOS")
        self.modules_label = tk.Label(
            master, bg=self.PANEL, fg=self.MUTED, justify="left", anchor="nw",
        )
        self.modules_label.pack(fill="x", padx=12)
        self._panel_title(master, "DESEMPENHO")
        self.performance_label = tk.Label(
            master, text="Coletando…", bg=self.PANEL, fg=self.MUTED,
            justify="left", anchor="nw",
        )
        self.performance_label.pack(fill="x", padx=12)
        spacer = tk.Frame(master, bg=self.PANEL)
        spacer.pack(fill="both", expand=True)
        ttk.Button(master, text="Voz", command=self.open_voice_settings).pack(fill="x", padx=10, pady=2)
        ttk.Button(master, text="Memórias", command=self.open_memories).pack(fill="x", padx=10, pady=2)
        ttk.Button(master, text="Configurações", command=self.open_settings).pack(fill="x", padx=10, pady=(2, 10))

    def _append(self, tag: str, label: str, text: str) -> None:
        self.history.configure(state="normal")
        self.history.insert("end", f"{label}\n", tag)
        self.history.insert("end", text + "\n", "body")
        self.history.configure(state="disabled")
        self.history.see("end")

    def send_entry(self) -> None:
        text = self.entry.get().strip()
        if text:
            self.entry.delete(0, "end")
            self.submit_text(text)

    def submit_text(self, text: str, show_window: bool = True) -> None:
        if show_window:
            self.show()
        self._append("user", "Você", text)
        self.graph.activate_terms(text)
        self._set_state(AppState.PROCESSING)

        def work() -> None:
            response = self.assistant.handle(text)
            self.root.after(0, self._finish_response, response)

        threading.Thread(target=work, name="NatyCommand", daemon=True).start()

    def _finish_response(self, response: str) -> None:
        self._append("naty", "Naty", response)
        self.mini.set_status("Concluído")
        self.mini.after(1600, self.mini.hide)
        self._set_state(AppState.IDLE)
        self._refresh_dashboard()
        if self.settings.tts_enabled:
            self._set_state(AppState.SPEAKING)
            spoken = response.split("\n\nFontes:", 1)[0]
            self.voice.speak_async(spoken, lambda: self.root.after(0, self._set_state, AppState.IDLE))

    def _set_state(self, state: AppState) -> None:
        self._last_state = state
        self.state.set_state(state)
        self.graph.set_state(state)

    def listen(self, show_window: bool = True) -> None:
        self._listening_from_mini = not show_window
        if show_window:
            self.show()
        if not self.settings.voice_enabled:
            self._append("naty", "Naty", "O reconhecimento de voz está desativado. Abra Voz para configurar.")
            return
        self._set_state(AppState.LISTENING)
        self.mini.set_status("Ouvindo…")
        self.voice.listen_async(
            lambda text: self.root.after(0, self._heard, text),
            lambda error: self.root.after(0, self._voice_error, error),
            timeout=8,
        )

    def _heard(self, text: str) -> None:
        if text:
            self.submit_text(text, show_window=not self._listening_from_mini)
        else:
            self._voice_error("Não detectei fala.")

    def _voice_error(self, error: str) -> None:
        self._set_state(AppState.ERROR)
        self.mini.set_status(error)
        self._append("naty", "Naty", error)
        self.root.after(1400, self._set_state, AppState.IDLE)

    def _refresh_dashboard(self) -> None:
        self.today_list.delete(0, "end")
        self._today_task_ids: list[int] = []
        today = datetime.now().astimezone().date().isoformat()
        for task in self.assistant.task_repo.list("pending")[:30]:
            due = (task.get("due_at") or "")[:10]
            if not due or due <= today:
                marker = "!" if task.get("priority") == "high" else "·"
                suffix = f"  {due}" if due else ""
                self.today_list.insert("end", f"{marker} {task['title']}{suffix}")
                self._today_task_ids.append(int(task["id"]))
        if not self._today_task_ids:
            self.today_list.insert("end", "Tudo livre por aqui.")
        entity = self.assistant.context.last_entity
        if entity:
            self.context_label.configure(text=f"{entity.type}\n{entity.label or entity.id}")
        else:
            self.context_label.configure(text="Nenhum item em foco")
        self.modules_label.configure(text=self._module_status())
        try:
            nodes, edges = self.assistant.knowledge_graph.rebuild()
            self.graph.set_graph(nodes, edges)
        except Exception:
            self.assistant.logger.exception("Falha ao atualizar grafo visual")

    def _module_status(self) -> str:
        checks = [
            ("Banco local", True),
            ("Obsidian", self.assistant.obsidian.available),
            ("Voz STT", bool(self.settings.vosk_model_path)),
            ("IA local", self.assistant.ai.is_available()),
            ("Google", self.settings.google_enabled),
        ]
        return "\n".join(f"{'●' if enabled else '○'} {name}" for name, enabled in checks)

    def _performance_tick(self) -> None:
        if self._closing:
            return
        if self.settings.performance_monitor_enabled:
            sample = self.performance.snapshot(
                ai_loaded=getattr(self.assistant.ai, "loaded", False),
                stt_loaded=getattr(getattr(self, "voice", None), "stt_loaded", False),
            )
            rss = f"{sample['rss_mb']} MiB" if sample["rss_mb"] is not None else "indisponível"
            cpu = f"{sample['cpu']}%" if sample["cpu"] is not None else "indisponível"
            self.performance_label.configure(
                text=f"RAM  {rss}\nCPU  {cpu}\nIA  {'carregada' if sample['ai_loaded'] else 'em espera'}\nSTT  {'carregado' if sample['stt_loaded'] else 'em espera'}"
            )
        self.root.after(2500, self._performance_tick)

    def _complete_selected_task(self, _event: tk.Event) -> None:
        selected = self.today_list.curselection()
        if not selected or selected[0] >= len(self._today_task_ids):
            return
        task_id = self._today_task_ids[selected[0]]
        task = self.assistant.task_repo.get(task_id)
        if task and messagebox.askyesno("Naty", f"Concluir '{task['title']}'?", parent=self.root):
            self.assistant.task_repo.complete(task_id)
            self._refresh_dashboard()

    def show(self) -> None:
        self.root.after(0, self._show_now)

    def _show_now(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.entry.focus_set()

    def hide(self) -> None:
        self.root.withdraw()

    def show_mini(self) -> None:
        self.mini.show()
        if self.settings.voice_enabled:
            self.listen(False)

    def focus_task(self) -> None:
        self.show()
        self.entry.delete(0, "end")
        self.entry.insert(0, "cria tarefa ")
        self.entry.icursor("end")

    def open_shopping_list(self) -> None:
        self.submit_text("abre a lista de compras")

    def open_voice_settings(self) -> None:
        self.show()
        VoiceSettingsWindow(self.root, self.settings, self._reload_voice)

    def _reload_voice(self) -> None:
        self.voice = VoiceSessionManager(self.settings)
        self._refresh_dashboard()

    def open_settings(self) -> None:
        self.show()
        win = tk.Toplevel(self.root)
        win.title("Naty · Configurações")
        win.geometry("650x500")
        win.configure(bg=self.BG)
        win.transient(self.root)
        frame = ttk.Frame(win, padding=18)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)
        obsidian = tk.BooleanVar(value=self.settings.obsidian_enabled)
        startup = tk.BooleanVar(value=self.settings.start_with_windows)
        notifications = tk.BooleanVar(value=self.settings.notifications_enabled)
        proactivity = tk.BooleanVar(value=self.settings.proactivity_enabled)
        morning = tk.BooleanVar(value=self.settings.morning_briefing)
        evening = tk.BooleanVar(value=self.settings.evening_review)
        overdue = tk.BooleanVar(value=self.settings.overdue_followup)
        vault = tk.StringVar(value=self.settings.obsidian_vault_path)
        ttk.Label(frame, text="CONFIGURAÇÕES", font=("Segoe UI", 16, "bold"), foreground=self.CYAN).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 16))
        ttk.Checkbutton(frame, text="Sincronizar com Obsidian", variable=obsidian).grid(row=1, column=0, columnspan=3, sticky="w", pady=4)
        ttk.Label(frame, text="Pasta do Vault").grid(row=2, column=0, sticky="w", pady=6)
        ttk.Entry(frame, textvariable=vault).grid(row=2, column=1, sticky="ew")
        ttk.Button(frame, text="Escolher", command=lambda: vault.set(filedialog.askdirectory(parent=win) or vault.get())).grid(row=2, column=2, padx=4)
        ttk.Checkbutton(frame, text="Notificações locais", variable=notifications).grid(row=3, column=0, columnspan=3, sticky="w", pady=(14, 4))
        ttk.Checkbutton(frame, text="Proatividade", variable=proactivity).grid(row=4, column=0, columnspan=3, sticky="w", pady=4)
        ttk.Checkbutton(frame, text="Briefing da manhã", variable=morning).grid(row=5, column=0, columnspan=3, sticky="w", padx=20, pady=2)
        ttk.Checkbutton(frame, text="Revisão noturna", variable=evening).grid(row=6, column=0, columnspan=3, sticky="w", padx=20, pady=2)
        ttk.Checkbutton(frame, text="Acompanhar tarefas atrasadas", variable=overdue).grid(row=7, column=0, columnspan=3, sticky="w", padx=20, pady=2)
        ttk.Checkbutton(frame, text="Iniciar com o Windows", variable=startup).grid(row=8, column=0, columnspan=3, sticky="w", pady=(12,4))
        ttk.Label(frame, text="Voz, IA local e contas externas continuam opcionais. Mudanças de Vault entram em vigor ao reiniciar.", style="Muted.TLabel").grid(row=9, column=0, columnspan=3, sticky="w", pady=18)

        def save() -> None:
            old_startup = self.settings.start_with_windows
            self.settings.obsidian_enabled = obsidian.get()
            self.settings.obsidian_vault_path = vault.get().strip()
            self.settings.naty_obsidian_path = str(Path(self.settings.obsidian_vault_path) / "Naty") if self.settings.obsidian_vault_path else ""
            self.settings.notifications_enabled = notifications.get()
            self.settings.proactivity_enabled = proactivity.get()
            self.settings.morning_briefing = morning.get()
            self.settings.evening_review = evening.get()
            self.settings.overdue_followup = overdue.get()
            self.settings.start_with_windows = startup.get()
            self.settings.save()
            if notifications.get():
                self.scheduler.start()
            else:
                self.scheduler.stop()
            if old_startup != startup.get():
                try:
                    from tools.system import set_start_with_windows
                    set_start_with_windows(startup.get())
                except Exception as exc:
                    messagebox.showwarning("Naty", f"Não foi possível alterar o startup: {exc}", parent=win)
            win.destroy()

        ttk.Button(frame, text="Salvar", command=save).grid(row=10, column=2, sticky="e")

    def open_memories(self) -> None:
        self.show()
        win = tk.Toplevel(self.root)
        win.title("Naty · Memórias consentidas")
        win.geometry("680x390")
        frame = ttk.Frame(win, padding=12)
        frame.pack(fill="both", expand=True)
        tree = ttk.Treeview(frame, columns=("type", "key", "value"), show="headings")
        for key, label, width in (("type", "Tipo", 110), ("key", "Chave", 180), ("value", "Valor", 320)):
            tree.heading(key, text=label)
            tree.column(key, width=width)
        tree.pack(fill="both", expand=True)

        def reload() -> None:
            tree.delete(*tree.get_children())
            for memory in self.assistant.memory_repo.all():
                tree.insert("", "end", iid=str(memory["id"]), values=(memory["type"], memory["key"], memory["value"]))

        def delete() -> None:
            selected = tree.selection()
            if selected and messagebox.askyesno("Naty", "Excluir a memória selecionada?", parent=win):
                self.assistant.memory_repo.delete(int(selected[0]))
                reload()

        ttk.Button(frame, text="Excluir selecionada", command=delete).pack(anchor="e", pady=(8, 0))
        reload()

    def _notify(self, title: str, message: str) -> None:
        if self.tray.running:
            self.tray.notify(title, message)
        else:
            self.root.after(0, lambda: messagebox.showinfo(title, message, parent=self.root))

    def exit(self) -> None:
        if self._closing:
            return
        self._closing = True
        self.scheduler.stop()
        self.hotkey.stop()
        self.tray.stop()
        self.assistant.close()
        self.root.after(0, self.root.destroy)

    def run(self) -> None:
        self.root.mainloop()
