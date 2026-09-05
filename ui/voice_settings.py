from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk

from voice.devices import default_input_device_id, friendly_audio_error, list_microphones, resolve_microphone
from voice.sapi_tts import SapiTTS
from voice.vosk_stt import VoskSTT
from voice.whisper_setup import diagnostics as whisper_diagnostics


class VoiceSettingsWindow:
    def __init__(self, root, settings, on_saved=None):
        self.root, self.settings, self.on_saved = root, settings, on_saved
        self.win = tk.Toplevel(root)
        self.win.title("Naty · Configurações > Voz > Diagnóstico")
        self.win.geometry("780x680")
        self.win.minsize(700, 620)
        self.win.transient(root)
        self.microphones, self.voices = list_microphones(), SapiTTS.list_voices()
        self._levels: list[float] = []
        self._testing = False
        self._build()

    def _build(self) -> None:
        frame = ttk.Frame(self.win, padding=18)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)
        self.voice_enabled = tk.BooleanVar(value=self.settings.voice_enabled)
        self.tts_enabled = tk.BooleanVar(value=self.settings.tts_enabled)
        self.status = tk.StringVar(value="Pronto para diagnosticar.")
        self.transcription = tk.StringVar(value="Ainda não testado")
        self.latency = tk.StringVar(value="—")
        self.device_info = tk.StringVar()
        self.level = tk.DoubleVar(value=0)

        ttk.Label(frame, text="VOZ · DIAGNÓSTICO", font=("Segoe UI", 16, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 16)
        )
        ttk.Label(frame, text="Microfone").grid(row=1, column=0, sticky="w")
        names = [self._device_label(device) for device in self.microphones]
        resolved = resolve_microphone(self.settings.microphone_device,
                                      getattr(self.settings, "microphone_name", ""),
                                      getattr(self.settings, "microphone_hostapi", ""),
                                      getattr(self.settings, "microphone_sample_rate", 0))
        current_id = resolved["id"] if resolved else self.settings.microphone_device
        current = next((name for name in names if name.startswith(f"{current_id} ·")),
                       next((name for name in names if "[padrão]" in name), names[0] if names else "Nenhum microfone"))
        self.mic = tk.StringVar(value=current)
        combo = ttk.Combobox(frame, textvariable=self.mic, values=names, state="readonly")
        combo.grid(row=1, column=1, sticky="ew", padx=8)
        combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_device_info())
        self.test_button = ttk.Button(frame, text="TESTAR MICROFONE", command=self.test_mic)
        self.test_button.grid(row=1, column=2)

        ttk.Label(frame, textvariable=self.device_info, wraplength=650).grid(
            row=2, column=0, columnspan=3, sticky="w", pady=(8, 12)
        )
        ttk.Label(frame, text="Nível em tempo real").grid(row=3, column=0, sticky="w")
        ttk.Progressbar(frame, variable=self.level, maximum=100).grid(row=3, column=1, columnspan=2, sticky="ew", padx=(8, 0))
        self.waveform = tk.Canvas(frame, height=72, background="#071017", highlightthickness=1,
                                  highlightbackground="#234454")
        self.waveform.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(7, 14))

        stt = VoskSTT(self.settings.vosk_model_path, device=self.selected_device(),
                      microphone_gain=self.settings.microphone_gain,
                      automatic_gain=self.settings.automatic_gain_enabled).diagnostics()
        whisper = whisper_diagnostics(self.settings.whisper_executable_path, self.settings.whisper_model_path)
        if self.settings.stt_provider == "whisper_cpp":
            model_text = whisper["status"]
        else:
            ready = stt["vosk_installed"] and stt["sounddevice_installed"] and stt["model_available"]
            model_text = f"Vosk {'pronto' if ready else 'incompleto'} · {stt['model_path']}"
        ttk.Label(frame, text="STT / modelo").grid(row=5, column=0, sticky="w")
        ttk.Label(frame, text=model_text, wraplength=460).grid(row=5, column=1, sticky="w", padx=8)
        ttk.Button(frame, text="Configurar", command=self.configure_whisper).grid(row=5, column=2, sticky="e")
        ttk.Label(frame, text="Última transcrição").grid(row=6, column=0, sticky="nw", pady=(10, 0))
        ttk.Label(frame, textvariable=self.transcription, wraplength=570).grid(
            row=6, column=1, columnspan=2, sticky="w", padx=8, pady=(10, 0))
        ttk.Label(frame, text="Latência").grid(row=7, column=0, sticky="w", pady=(8, 14))
        ttk.Label(frame, textvariable=self.latency).grid(row=7, column=1, sticky="w", padx=8, pady=(8, 14))

        ttk.Separator(frame).grid(row=8, column=0, columnspan=3, sticky="ew", pady=4)
        ttk.Label(frame, text="Voz da Naty").grid(row=9, column=0, sticky="w", pady=(12, 0))
        voice_labels = [self._voice_label(voice) for voice in self.voices]
        preferred = self.settings.voice or SapiTTS.preferred_voice()
        selected_voice = next((label for label in voice_labels if label.startswith(preferred + " ·")),
                              voice_labels[0] if voice_labels else "Nenhuma voz SAPI")
        self.voice = tk.StringVar(value=selected_voice)
        ttk.Combobox(frame, textvariable=self.voice, values=voice_labels, state="readonly").grid(
            row=9, column=1, sticky="ew", padx=8, pady=(12, 0))
        ttk.Button(frame, text="Ouvir exemplo", command=self.test_tts).grid(row=9, column=2, pady=(12, 0))
        if not any(v.get("gender", "").casefold() == "female" and v.get("culture", "").casefold().startswith("pt-br") for v in self.voices):
            ttk.Label(frame, text=SapiTTS.windows_voice_setup_instructions(), wraplength=700).grid(
                row=10, column=0, columnspan=3, sticky="w", pady=(6, 0))

        ttk.Label(frame, text="Ganho máximo do microfone").grid(row=11, column=0, sticky="w", pady=(12, 0))
        self.gain = tk.DoubleVar(value=self.settings.microphone_gain)
        ttk.Scale(frame, from_=1, to=20, variable=self.gain).grid(row=11, column=1, sticky="ew", padx=8, pady=(12, 0))
        self.auto_gain = tk.BooleanVar(value=self.settings.automatic_gain_enabled)
        ttk.Checkbutton(frame, text="automático", variable=self.auto_gain).grid(row=11, column=2, sticky="w", pady=(12, 0))
        ttk.Label(frame, text="Velocidade").grid(row=12, column=0, sticky="w", pady=(12, 0))
        self.rate = tk.IntVar(value=self.settings.voice_rate)
        ttk.Scale(frame, from_=-5, to=5, variable=self.rate).grid(row=12, column=1, sticky="ew", padx=8, pady=(12, 0))
        ttk.Label(frame, text="Volume").grid(row=13, column=0, sticky="w", pady=(8, 0))
        self.volume = tk.IntVar(value=self.settings.voice_volume)
        ttk.Scale(frame, from_=0, to=100, variable=self.volume).grid(row=13, column=1, sticky="ew", padx=8, pady=(8, 0))
        ttk.Label(frame, text="Continuação da conversa").grid(row=14, column=0, sticky="w", pady=(8, 0))
        self.followup = tk.IntVar(value=max(5, min(15, int(self.settings.conversation_followup_seconds))))
        ttk.Spinbox(frame, from_=5, to=15, width=5, textvariable=self.followup).grid(row=14, column=1, sticky="w", padx=8, pady=(8, 0))
        ttk.Label(frame, text="segundos (5–15)").grid(row=14, column=1, sticky="w", padx=(65, 0), pady=(8, 0))

        toggles = ttk.Frame(frame)
        toggles.grid(row=15, column=0, columnspan=3, sticky="w", pady=(14, 4))
        ttk.Checkbutton(toggles, text="Reconhecimento de voz", variable=self.voice_enabled).pack(side="left")
        ttk.Checkbutton(toggles, text="Resposta falada", variable=self.tts_enabled).pack(side="left", padx=16)
        ttk.Label(frame, textvariable=self.status, wraplength=700).grid(row=16, column=0, columnspan=3, sticky="w", pady=8)
        ttk.Button(frame, text="Salvar", command=self.save).grid(row=17, column=2, sticky="e")
        self._refresh_device_info()

    @staticmethod
    def _device_label(device: dict) -> str:
        suffix = " [padrão]" if device.get("is_default") else ""
        return f"{device['id']} · {device['name']} · {device.get('hostapi', '')}{suffix}"

    @staticmethod
    def _voice_label(voice: dict) -> str:
        return f"{voice['name']} · {voice.get('culture') or '?'} · {voice.get('gender') or '?'}"

    def selected_device(self) -> int:
        try: return int(self.mic.get().split("·", 1)[0].strip())
        except ValueError: return -1

    def selected_voice(self) -> str:
        return self.voice.get().split(" · ", 1)[0].strip() if self.voices else ""

    def _refresh_device_info(self) -> None:
        selected = next((d for d in self.microphones if d["id"] == self.selected_device()), None)
        default = next((d for d in self.microphones if d.get("is_default")), None)
        if not selected:
            self.device_info.set("Nenhum dispositivo de entrada disponível.")
            return
        self.device_info.set(
            f"Dispositivo padrão: {default['name'] if default else default_input_device_id()}  ·  "
            f"Selecionado: {selected['channels']} canal(is), {selected['default_samplerate']} Hz, {selected.get('hostapi') or 'API não informada'}"
        )

    def _update_level(self, value: float) -> None:
        self.level.set(value * 100)
        self._levels.append(value)
        self._levels = self._levels[-64:]
        self.waveform.delete("all")
        width = max(1, self.waveform.winfo_width()); height = max(1, self.waveform.winfo_height())
        step = width / max(1, len(self._levels))
        for index, level in enumerate(self._levels):
            bar = max(1, level * height * 2.5)
            x = index * step
            self.waveform.create_line(x, (height - bar) / 2, x, (height + bar) / 2, fill="#55e6ff", width=max(1, int(step - 1)))

    def test_mic(self) -> None:
        if self._testing: return
        model = Path(self.settings.vosk_model_path)
        if not model.is_dir():
            self.status.set("Modelo Vosk não encontrado. Execute setup_voice.bat e confira o caminho exibido acima.")
            return
        self._testing = True; self._levels.clear(); self.transcription.set("Aguardando teste…"); self.latency.set("—")
        self.test_button.configure(state="disabled")
        self._countdown(2)

    def _countdown(self, seconds: int) -> None:
        if seconds:
            self.status.set(f"O teste começa em {seconds}…")
            self.win.after(1000, self._countdown, seconds - 1)
            return
        self.status.set("Ouvindo por até 7 segundos. Fale uma frase normalmente.")
        started = time.perf_counter()

        def work() -> None:
            try:
                stt = VoskSTT(self.settings.vosk_model_path, device=self.selected_device(),
                              microphone_gain=float(self.gain.get()), automatic_gain=self.auto_gain.get())
                text = stt.listen_once(7, on_level=lambda value: self.win.after(0, self._update_level, value))
                elapsed = (time.perf_counter() - started) * 1000
                self.win.after(0, self._finish_mic_test, text, elapsed, "")
            except Exception as exc:
                elapsed = (time.perf_counter() - started) * 1000
                self.win.after(0, self._finish_mic_test, "", elapsed, friendly_audio_error(exc))
        threading.Thread(target=work, name="NatyMicDiagnostic", daemon=True).start()

    def _finish_mic_test(self, text: str, latency_ms: float, error: str) -> None:
        self._testing = False; self.test_button.configure(state="normal"); self.latency.set(f"{latency_ms:.0f} ms")
        peak = max(self._levels or [0.0])
        if error:
            self.transcription.set("Falha na captura")
            self.status.set(error)
        elif text:
            self.transcription.set(text)
            self.status.set(f"Teste concluído. Pico do microfone: {peak * 100:.1f}%.")
        elif peak < 0.003:
            self.transcription.set("Nenhuma fala detectada")
            self.status.set("O dispositivo abriu, mas não houve sinal útil. Confira mute, ganho e o microfone selecionado.")
        else:
            self.transcription.set("Áudio sem palavras reconhecidas")
            self.status.set("O microfone recebeu sinal, mas o Vosk não reconheceu a frase. Fale mais perto e reduza ruído ambiente.")

    def test_tts(self) -> None:
        self.status.set("Reproduzindo exemplo…")
        def work() -> None:
            SapiTTS(self.selected_voice(), int(self.rate.get()), int(self.volume.get())).speak("Olá. Esta é a voz da Naty.")
            self.win.after(0, self.status.set, "Exemplo concluído.")
        threading.Thread(target=work, name="NatyVoicePreview", daemon=True).start()

    def configure_whisper(self) -> None:
        script = Path(__file__).resolve().parents[1] / "scripts" / "setup_whisper.py"
        flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
        subprocess.Popen([sys.executable, str(script)], creationflags=flags)
        self.status.set("Configuração do Whisper aberta. Reabra esta tela quando ela terminar.")

    def save(self) -> None:
        self.settings.voice_enabled = self.voice_enabled.get()
        self.settings.tts_enabled = self.tts_enabled.get()
        self.settings.microphone_device = self.selected_device()
        selected = next((device for device in self.microphones if device["id"] == self.settings.microphone_device), None)
        if selected:
            self.settings.microphone_name = selected["name"]
            self.settings.microphone_hostapi = selected.get("hostapi", "")
            self.settings.microphone_sample_rate = int(selected.get("default_samplerate", 0))
        self.settings.microphone_gain = max(1.0, min(20.0, float(self.gain.get())))
        self.settings.automatic_gain_enabled = self.auto_gain.get()
        self.settings.voice = self.selected_voice()
        self.settings.voice_rate = int(self.rate.get())
        self.settings.voice_volume = int(self.volume.get())
        self.settings.conversation_followup_seconds = max(5, min(15, int(self.followup.get())))
        self.settings.save()
        if self.on_saved: self.on_saved()
        self.win.destroy()
