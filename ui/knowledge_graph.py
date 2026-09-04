from __future__ import annotations

import math
import time
import tkinter as tk


COLORS = {"agent": "#55e6ff", "project": "#9b8cff", "note": "#3da9fc", "concept": "#4dd4ac", "memory": "#ffcf66", "task": "#8aa4bd"}


class KnowledgeGraphCanvas(tk.Canvas):
    """Visualiza relações; nunca exibe raciocínio interno."""
    def __init__(self, master, **kwargs):
        super().__init__(master, bg="#07111f", highlightthickness=0, **kwargs)
        self.nodes, self.edges, self.state = [], [], "IDLE"
        self._positions, self._visible, self._phase = {}, True, 0.0
        self.bind("<Configure>", lambda _: self.redraw())
        self.bind("<Map>", self._on_map); self.bind("<Unmap>", self._on_unmap)
        self.after(400, self._tick)

    def set_graph(self, nodes, edges): self.nodes, self.edges = list(nodes), list(edges); self.redraw()
    def set_state(self, state): self.state = getattr(state, "value", str(state)); self.redraw()
    def activate_terms(self, text: str):
        terms = {w.casefold() for w in text.split() if len(w) > 2}
        for node in self.nodes: node.active = any(term in node.title.casefold() for term in terms)
        self.redraw()

    def _on_map(self, _): self._visible = True
    def _on_unmap(self, _): self._visible = False

    def _tick(self):
        if self._visible:
            self._phase = time.monotonic(); self.redraw()
        interval = 100 if self.state in {"LISTENING", "PROCESSING", "RETRIEVING", "RESEARCHING", "SPEAKING", "GMAIL"} else 650
        self.after(interval, self._tick)

    def redraw(self):
        if not self._visible: return
        self.delete("all"); width, height = max(self.winfo_width(), 300), max(self.winfo_height(), 240)
        cx, cy = width / 2, height / 2; shown = self.nodes[:22]
        center = next((n for n in shown if n.id == "naty"), None)
        outer = [n for n in shown if n.id != "naty"]
        positions = {"naty": (cx, cy)}
        radius = min(width, height) * 0.35
        for index, node in enumerate(outer):
            angle = (2 * math.pi * index / max(1, len(outer))) - math.pi / 2
            ring = radius * (0.62 if index % 3 == 0 else 1.0)
            positions[node.id] = (cx + math.cos(angle) * ring, cy + math.sin(angle) * ring)
        self._positions = positions
        for edge in self.edges:
            if edge.source in positions and edge.target in positions:
                x1,y1=positions[edge.source]; x2,y2=positions[edge.target]
                self.create_line(x1,y1,x2,y2,fill="#173853",width=1)
        pulse = 3 + int((math.sin(self._phase * 4) + 1) * 2) if self.state != "IDLE" else 2
        for node in shown:
            x,y=positions[node.id]; base = 18 if node.id == "naty" else 7 + min(5, int(node.importance))
            size = base + (pulse if node.active or (node.id == "naty" and self.state != "IDLE") else 0)
            color = COLORS.get(node.type, "#607d98")
            self.create_oval(x-size,y-size,x+size,y+size,fill="#0b1e30",outline=color,width=2)
            if node.id == "naty" or node.active or len(shown) <= 12:
                self.create_text(x,y+size+11,text=node.title[:24],fill="#c8e7f5",font=("Segoe UI",8))
        self.create_text(12,12,anchor="nw",text="MENTE NATY  ·  conhecimento e relações",fill="#4e7f9d",font=("Segoe UI",8))
