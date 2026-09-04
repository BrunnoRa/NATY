from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from voice.devices import list_microphones
from voice.sapi_tts import SapiTTS
from voice.vosk_stt import VoskSTT


class VoiceSettingsWindow:
    def __init__(self, root, settings, on_saved=None):
        self.root, self.settings, self.on_saved = root, settings, on_saved
        self.win = tk.Toplevel(root); self.win.title("Naty · Voz"); self.win.geometry("660x480"); self.win.transient(root)
        self.microphones, self.voices = list_microphones(), SapiTTS.list_voices()
        self._build()

    def _build(self):
        f=ttk.Frame(self.win,padding=18); f.pack(fill="both",expand=True); f.columnconfigure(1,weight=1)
        self.voice_enabled=tk.BooleanVar(value=self.settings.voice_enabled); self.tts_enabled=tk.BooleanVar(value=self.settings.tts_enabled)
        ttk.Label(f,text="VOZ",font=("Segoe UI",16,"bold")).grid(row=0,column=0,columnspan=3,sticky="w",pady=(0,16))
        ttk.Label(f,text="Microfone").grid(row=1,column=0,sticky="w")
        names=[f"{d['id']} · {d['name']}" for d in self.microphones]; current=next((n for n in names if n.startswith(str(self.settings.microphone_device)+" ")), names[0] if names else "Nenhum microfone")
        self.mic=tk.StringVar(value=current); ttk.Combobox(f,textvariable=self.mic,values=names,state="readonly").grid(row=1,column=1,sticky="ew",padx=8)
        ttk.Button(f,text="Testar microfone",command=self.test_mic).grid(row=1,column=2)
        installed = bool(self.settings.vosk_model_path)
        ttk.Label(f,text="STT").grid(row=2,column=0,sticky="w",pady=12); ttk.Label(f,text=f"Vosk pt-BR  {'✓ instalado' if installed else '○ não instalado'}").grid(row=2,column=1,sticky="w")
        ttk.Label(f,text="Voz da Naty").grid(row=3,column=0,sticky="w")
        voice_names=[v["name"] for v in self.voices]; self.voice=tk.StringVar(value=self.settings.voice or SapiTTS.preferred_voice())
        ttk.Combobox(f,textvariable=self.voice,values=voice_names,state="readonly").grid(row=3,column=1,sticky="ew",padx=8); ttk.Button(f,text="Ouvir exemplo",command=self.test_tts).grid(row=3,column=2)
        ttk.Label(f,text="Velocidade").grid(row=4,column=0,sticky="w",pady=12); self.rate=tk.IntVar(value=self.settings.voice_rate); ttk.Scale(f,from_=-5,to=5,variable=self.rate).grid(row=4,column=1,sticky="ew")
        ttk.Label(f,text="Volume").grid(row=5,column=0,sticky="w"); self.volume=tk.IntVar(value=self.settings.voice_volume); ttk.Scale(f,from_=0,to=100,variable=self.volume).grid(row=5,column=1,sticky="ew")
        toggles=ttk.Frame(f); toggles.grid(row=6,column=0,columnspan=3,sticky="w",pady=(16,4)); ttk.Checkbutton(toggles,text="Reconhecimento de voz",variable=self.voice_enabled).pack(side="left"); ttk.Checkbutton(toggles,text="Resposta falada",variable=self.tts_enabled).pack(side="left",padx=16)
        ttk.Label(f,text="Push-to-talk: Ctrl + Alt + Espaço\nWake word: desligado",foreground="#6f91a5").grid(row=7,column=0,columnspan=3,sticky="w",pady=12)
        ttk.Button(f,text="Salvar",command=self.save).grid(row=8,column=2,sticky="e")

    def selected_device(self):
        try: return int(self.mic.get().split("·",1)[0].strip())
        except ValueError: return -1

    def test_mic(self):
        if not self.settings.vosk_model_path: messagebox.showwarning("Naty","Instale o modelo com setup_voice.bat.",parent=self.win); return
        def work():
            try: text=VoskSTT(self.settings.vosk_model_path,device=self.selected_device()).listen_once(6); msg=text or "Silêncio ou áudio incompreensível."
            except Exception as exc: msg=str(exc)
            self.win.after(0,lambda: messagebox.showinfo("Teste de microfone",msg,parent=self.win))
        threading.Thread(target=work,daemon=True).start()

    def test_tts(self):
        threading.Thread(target=lambda:SapiTTS(self.voice.get(),int(self.rate.get()),int(self.volume.get())).speak("Olá. Esta é a voz da Naty."),daemon=True).start()

    def save(self):
        self.settings.voice_enabled=self.voice_enabled.get(); self.settings.tts_enabled=self.tts_enabled.get(); self.settings.microphone_device=self.selected_device(); self.settings.voice=self.voice.get(); self.settings.voice_rate=int(self.rate.get()); self.settings.voice_volume=int(self.volume.get()); self.settings.save()
        if self.on_saved: self.on_saved()
        self.win.destroy()
