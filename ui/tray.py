from __future__ import annotations

import threading


class TrayIcon:
    def __init__(self, on_open, on_listen, on_task, on_list, on_settings, on_exit):
        self.callbacks = on_open, on_listen, on_task, on_list, on_settings, on_exit
        self.icon = None; self.running = False

    def start(self) -> bool:
        try:
            import pystray
            from PIL import Image, ImageDraw
        except ImportError: return False
        image = Image.new("RGBA", (64, 64), (12, 18, 28, 255)); draw = ImageDraw.Draw(image)
        draw.ellipse((10, 10, 54, 54), outline=(86, 215, 230, 255), width=5); draw.ellipse((27, 27, 37, 37), fill=(86, 215, 230, 255))
        o, l, t, li, s, e = self.callbacks
        menu = pystray.Menu(
            pystray.MenuItem("Abrir Naty", lambda: o(), default=True),
            pystray.MenuItem("Ouvir", lambda: l()),
            pystray.MenuItem("Nova tarefa", lambda: t()),
            pystray.MenuItem("Lista de compras", lambda: li()),
            pystray.MenuItem("Configurações", lambda: s()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Sair", lambda: e()),
        )
        self.icon = pystray.Icon("Naty", image, "Naty", menu); self.running = True
        threading.Thread(target=self.icon.run, name="NatyTray", daemon=True).start(); return True

    def notify(self, title: str, message: str) -> None:
        if self.icon:
            try: self.icon.notify(message, title)
            except Exception: pass

    def stop(self) -> None:
        self.running = False
        if self.icon:
            try: self.icon.stop()
            except Exception: pass
