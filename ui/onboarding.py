from __future__ import annotations

import importlib.util
from pathlib import Path
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


class OnboardingWizard:
    def __init__(self, root, assistant, on_done=None):
        self.root,self.assistant,self.settings,self.on_done=root,assistant,assistant.settings,on_done
        self.win=tk.Toplevel(root); self.win.title("Primeira configuração da Naty"); self.win.geometry("680x590"); self.win.transient(root); self.win.grab_set()
        self.step=0; self.frames=[]; self._build(); self.show(0)

    def _build(self):
        self.body=ttk.Frame(self.win,padding=24); self.body.pack(fill="both",expand=True)
        self.name=tk.StringVar(value=self.settings.user_name); self.language=tk.StringVar(value=self.settings.language); self.vault=tk.StringVar(value=self.settings.obsidian_vault_path)
        self.prepare=tk.BooleanVar(value=True); self.briefing=tk.BooleanVar(value=False); self.evening=tk.BooleanVar(value=False); self.followup=tk.BooleanVar(value=True)
        self.voice_enabled=tk.BooleanVar(value=self.settings.voice_enabled); self.tts_enabled=tk.BooleanVar(value=self.settings.tts_enabled)
        self.local_ai=tk.BooleanVar(value=self.settings.ai_enabled); self.connect_google=tk.BooleanVar(value=False); self.google_credentials=tk.StringVar(value=self.settings.google_credentials_path)
        pages=[]
        p=ttk.Frame(self.body); ttk.Label(p,text="Vamos configurar a Naty",font=("Segoe UI",18,"bold")).pack(anchor="w"); ttk.Label(p,text="Como devo chamar você?").pack(anchor="w",pady=(24,4)); ttk.Entry(p,textvariable=self.name).pack(fill="x"); ttk.Label(p,text="Idioma").pack(anchor="w",pady=(14,4)); ttk.Combobox(p,textvariable=self.language,values=["pt-BR"],state="readonly").pack(fill="x"); pages.append(p)
        p=ttk.Frame(self.body); ttk.Label(p,text="Seu cérebro externo",font=("Segoe UI",18,"bold")).pack(anchor="w"); ttk.Label(p,text="Escolha um Vault do Obsidian. Nenhum arquivo pessoal será apagado.").pack(anchor="w",pady=(16,8)); row=ttk.Frame(p); row.pack(fill="x"); ttk.Entry(row,textvariable=self.vault).pack(side="left",fill="x",expand=True); ttk.Button(row,text="Escolher",command=lambda:self.vault.set(filedialog.askdirectory(parent=self.win) or self.vault.get())).pack(side="left",padx=6); ttk.Checkbutton(p,text="Preparar a estrutura Naty neste Vault",variable=self.prepare).pack(anchor="w",pady=14); pages.append(p)
        p=ttk.Frame(self.body); ttk.Label(p,text="Voz local",font=("Segoe UI",18,"bold")).pack(anchor="w"); ttk.Label(p,text="O Windows SAPI fala sem download. Para reconhecer voz em pt-BR, execute setup_voice.bat; ele informa e confirma o modelo antes de baixar.",wraplength=590).pack(anchor="w",pady=18); ttk.Checkbutton(p,text="Ativar reconhecimento de voz",variable=self.voice_enabled).pack(anchor="w",pady=3); ttk.Checkbutton(p,text="Ativar resposta falada",variable=self.tts_enabled).pack(anchor="w",pady=3); ttk.Label(p,text=f"Modelo Vosk: {'instalado' if self.settings.vosk_model_path else 'ainda não configurado'}").pack(anchor="w",pady=12); pages.append(p)
        p=ttk.Frame(self.body); ttk.Label(p,text="Proatividade e integrações",font=("Segoe UI",18,"bold")).pack(anchor="w"); ttk.Checkbutton(p,text="Briefing pela manhã",variable=self.briefing).pack(anchor="w",pady=(14,3)); ttk.Checkbutton(p,text="Revisão noturna",variable=self.evening).pack(anchor="w",pady=3); ttk.Checkbutton(p,text="Acompanhar tarefas atrasadas",variable=self.followup).pack(anchor="w",pady=3); ttk.Checkbutton(p,text="Habilitar conversa local se o modelo já estiver instalado",variable=self.local_ai).pack(anchor="w",pady=(12,3)); ttk.Label(p,text="Sem modelo? Conclua e execute setup_ai.bat; tamanho e licença aparecem antes do download.",wraplength=590).pack(anchor="w"); ttk.Checkbutton(p,text="Conectar Gmail e Calendar ao concluir",variable=self.connect_google).pack(anchor="w",pady=(12,3)); google_row=ttk.Frame(p); google_row.pack(fill="x"); ttk.Entry(google_row,textvariable=self.google_credentials).pack(side="left",fill="x",expand=True); ttk.Button(google_row,text="JSON OAuth",command=lambda:self.google_credentials.set(filedialog.askopenfilename(parent=self.win,filetypes=[("Credencial Google","*.json")]) or self.google_credentials.get())).pack(side="left",padx=6); ttk.Label(p,text="Nenhum modelo, conta ou custo é ativado sem sua escolha.",wraplength=590).pack(anchor="w",pady=12); pages.append(p)
        self.frames=pages
        nav=ttk.Frame(self.win,padding=(24,8,24,20)); nav.pack(fill="x"); self.back=ttk.Button(nav,text="Voltar",command=lambda:self.show(self.step-1)); self.back.pack(side="left"); self.next=ttk.Button(nav,text="Próximo",command=self.advance); self.next.pack(side="right")

    def show(self,index):
        self.step=max(0,min(index,len(self.frames)-1))
        for f in self.frames: f.pack_forget()
        self.frames[self.step].pack(fill="both",expand=True); self.back.configure(state="disabled" if self.step==0 else "normal"); self.next.configure(text="Concluir" if self.step==len(self.frames)-1 else "Próximo")

    def advance(self):
        if self.step<len(self.frames)-1: self.show(self.step+1); return
        self.settings.user_name=self.name.get().strip(); self.settings.language=self.language.get(); self.settings.obsidian_vault_path=self.vault.get().strip(); self.settings.naty_obsidian_path=str(Path(self.settings.obsidian_vault_path) / "Naty") if self.settings.obsidian_vault_path else ""; self.settings.obsidian_enabled=bool(self.vault.get().strip()); self.settings.voice_enabled=self.voice_enabled.get(); self.settings.tts_enabled=self.tts_enabled.get(); self.settings.proactivity_enabled=self.briefing.get() or self.evening.get() or self.followup.get(); self.settings.morning_briefing=self.briefing.get(); self.settings.evening_review=self.evening.get(); self.settings.overdue_followup=self.followup.get(); self.settings.google_credentials_path=self.google_credentials.get().strip(); self.settings.first_run_completed=True
        self.settings.ai_enabled=bool(self.local_ai.get() and self.settings.ai_model_path and Path(self.settings.ai_model_path).is_file() and importlib.util.find_spec("llama_cpp"))
        if self.settings.user_name: self.assistant.memory_repo.set("preference","user_name",self.settings.user_name)
        if self.prepare.get() and self.settings.obsidian_enabled:
            try:
                from knowledge.obsidian_bootstrap import ObsidianBootstrap
                ObsidianBootstrap(self.settings.obsidian_vault_path, self.settings.naty_obsidian_path).prepare()
            except Exception as exc: messagebox.showwarning("Naty",f"Não foi possível preparar o Vault: {exc}",parent=self.win)
        self.settings.save(); self.win.destroy()
        if self.on_done: self.on_done()
        if self.local_ai.get() and not self.settings.ai_enabled:
            messagebox.showinfo("Naty", "A conversa local não foi ativada porque modelo/llama-cpp ainda não estão instalados. Execute setup_ai.bat.", parent=self.root)
        if self.connect_google.get():
            if not self.settings.google_credentials_path:
                messagebox.showwarning("Naty", "Escolha o JSON OAuth para conectar o Google.", parent=self.root)
            else:
                google = self.assistant.tool_router.google
                google.auth.credentials_path = Path(self.settings.google_credentials_path)
                def connect():
                    result = google.connect()
                    self.root.after(0, lambda: messagebox.showinfo("Naty · Google", result.message, parent=self.root))
                threading.Thread(target=connect, name="NatyGoogleOAuth", daemon=True).start()
