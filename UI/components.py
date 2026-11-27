from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk
from typing import Any, Callable, Dict, Iterable, List, Optional

try:
    from Source.game_engine import STATUS_CRIMINAL, STATUS_INNOCENT, STATUS_UNKNOWN
except Exception: 
    STATUS_CRIMINAL, STATUS_INNOCENT, STATUS_UNKNOWN = "CRIMINAL", "INNOCENT", "UNKNOWN"

BG = "#F3EDE2"          # nền cửa sổ
SURFACE = "#FCF9F3"     # nền panel / thẻ chưa lật
SURFACE_HI = "#EAE1D4"  # nền nổi hơn (hover, thẻ con trong panel)
BORDER = "#302A26"      # viền nâu đen

TEXT = "#302B28"        # chữ chính
MUTED = "#766E67"       # chữ phụ
DIM = "#524C47"         # chữ mờ
INK = "#302B28"         # chữ tối đặt trên nền màu sáng

ACCENT = "#FCB500"      # vùng được manh mối nhắc tới (clue region)
HINT = "#D49A2A"        # gợi ý

CRIMINAL = "#F35A5A"    # viền / điểm nhấn tội phạm
CRIMINAL_BG = "#F8C5C3"  # nền thẻ tội phạm

INNOCENT = "#45A568"     # viền / điểm nhấn vô tội
INNOCENT_BG = "#E5F0E2"  # nền thẻ vô tội

PANEL = SURFACE
UNKNOWN = MUTED
HIGHLIGHT = HINT

STATUS_STYLE: Dict[str, Dict[str, str]] = {
    STATUS_CRIMINAL: dict(label="Criminal", fill=CRIMINAL_BG, edge=CRIMINAL,
                          accent=CRIMINAL, pill=CRIMINAL, pill_fg=INK),
    STATUS_INNOCENT: dict(label="Innocent", fill=INNOCENT_BG, edge=INNOCENT,
                          accent=INNOCENT, pill=INNOCENT, pill_fg=INK),
    STATUS_UNKNOWN: dict(label="Unknown", fill=SURFACE, edge=BORDER,
                         accent=MUTED, pill="#2a3250", pill_fg=MUTED),
}

CLUE_LABELS = {
    "EXACTLY": "Exactly",
    "AT_LEAST": "At least",
    "AT_MOST": "At most",
    "SAME": "Same status",
    "DIFFERENT": "Different status",
    "FACT": "Fact",
}


def status_style(cell: Optional[Dict[str, Any]]) -> Dict[str, str]:
    if cell and cell.get("is_revealed"):
        return STATUS_STYLE.get(cell.get("status"), STATUS_STYLE[STATUS_UNKNOWN])
    return STATUS_STYLE[STATUS_UNKNOWN]


def clue_label(clue: Dict[str, Any]) -> str:
    ctype = str(clue.get("type", "")).upper()
    return CLUE_LABELS.get(ctype, ctype.replace("_", " ").capitalize() or "Clue")


def mix(a: str, b: str, t: float) -> str:
    a, b = a.lstrip("#"), b.lstrip("#")
    out = []
    for i in (0, 2, 4):
        x, y = int(a[i:i + 2], 16), int(b[i:i + 2], 16)
        out.append(round(x + (y - x) * t))
    return "#{:02x}{:02x}{:02x}".format(*out)



_families: Dict[str, str] = {}
_font_cache: Dict[Any, tkfont.Font] = {}


def _pick_family(candidates: Iterable[str], fallback: str) -> str:
    available = set(tkfont.families())
    for name in candidates:
        if name in available:
            return name
    return fallback


def ui_font(size: int = 10, bold: bool = False):
    if "ui" not in _families:
        _families["ui"] = _pick_family(
            ("Segoe UI", "SF Pro Text", "Helvetica Neue", "Inter",
             "Ubuntu", "Cantarell", "DejaVu Sans", "Arial"),
            "Helvetica",
        )
    family = _families["ui"]
    return (family, size, "bold") if bold else (family, size)


def text_width(text: str, font) -> int:
    f = _font_cache.get(font)
    if f is None:
        f = _font_cache[font] = tkfont.Font(font=font)
    return f.measure(text)


def fit_font(text: str, size: int, bold: bool, max_width: float, min_size: int = 8):
    while size > min_size and text_width(text, ui_font(size, bold)) > max_width:
        size -= 1
    return ui_font(size, bold)



def rounded_points(x1: float, y1: float, x2: float, y2: float, r: float) -> List[float]:
    r = max(0.0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    return [
        x1 + r, y1, x1 + r, y1, x2 - r, y1, x2 - r, y1,
        x2, y1, x2, y1 + r, x2, y1 + r, x2, y2 - r, x2, y2 - r,
        x2, y2, x2 - r, y2, x2 - r, y2, x1 + r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y2 - r, x1, y1 + r, x1, y1 + r,
        x1, y1,
    ]


def rounded_rect(canvas: tk.Canvas, x1, y1, x2, y2, r=12, **kw) -> int:
    return canvas.create_polygon(rounded_points(x1, y1, x2, y2, r), smooth=True, **kw)


def bind_tree(widget: tk.Misc, sequence: str, callback: Callable) -> None:
    widget.bind(sequence, callback, add="+")
    for child in widget.winfo_children():
        bind_tree(child, sequence, callback)


def auto_wrap(label: tk.Label, container: tk.Misc, margin: int = 0, minimum: int = 80) -> None:
    container.bind(
        "<Configure>",
        lambda e: label.configure(wraplength=max(e.width - margin, minimum)),
        add="+",
    )


def apply_theme(root: tk.Tk) -> None:
    root.configure(bg=BG)
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.layout(
        "Dark.Vertical.TScrollbar",
        [("Vertical.Scrollbar.trough", {
            "sticky": "ns",
            "children": [("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})],
        })],
    )
    style.configure(
        "Dark.Vertical.TScrollbar",
        troughcolor=SURFACE, background=BORDER, bordercolor=SURFACE,
        lightcolor=BORDER, darkcolor=BORDER, gripcount=0, width=8, relief="flat",
    )
    style.map("Dark.Vertical.TScrollbar", background=[("active", DIM), ("pressed", MUTED)])



class RoundedButton(tk.Canvas):

    STYLES = {
        "primary": dict(bg=ACCENT, hover="#7ad2ff", press="#35a9e6", fg=INK),
        "success": dict(bg=INNOCENT, hover="#5fe3b2", press="#26b883", fg=INK),
        "danger": dict(bg=CRIMINAL, hover="#ff8290", press="#e04558", fg=INK),
        "ghost": dict(bg=SURFACE_HI, hover="#303958", press="#1f2640", fg=TEXT),
    }

    def __init__(self, master, text: str, command: Callable[[], None], style: str = "ghost",
                 width: int = 120, height: int = 38, radius: int = 12, size: int = 10,
                 surface: str = BG):
        super().__init__(master, width=width, height=height, bg=surface,
                         highlightthickness=0, bd=0, cursor="hand2")
        self._text = text
        self._command = command
        self._style = self.STYLES[style]
        self._radius = radius
        self._size = size
        self._enabled = True
        self._hover = False
        self._pressed = False
        self.bind("<Configure>", lambda _e: self._draw())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self._draw()

    def set_enabled(self, enabled: bool) -> None:
        if enabled == self._enabled:
            return
        self._enabled = enabled
        self._hover = self._pressed = False
        self.configure(cursor="hand2" if enabled else "arrow")
        self._draw()

    def set_text(self, text: str) -> None:
        self._text = text
        self._draw()

    def set_style(self, style: str) -> None:
        self._style = self.STYLES[style]
        self._draw()

    def _on_enter(self, _e):
        self._hover = True
        self._draw()

    def _on_leave(self, _e):
        self._hover = self._pressed = False
        self._draw()

    def _on_press(self, _e):
        if self._enabled:
            self._pressed = True
            self._draw()

    def _on_release(self, e):
        was_pressed = self._pressed
        self._pressed = False
        self._draw()
        inside = 0 <= e.x <= self.winfo_width() and 0 <= e.y <= self.winfo_height()
        if self._enabled and was_pressed and inside:
            self._command()

    def _draw(self) -> None:
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 1:
            w = int(self.cget("width"))
        if h <= 1:
            h = int(self.cget("height"))
        st = self._style
        if not self._enabled:
            fill, fg, outline = "#212839", DIM, BORDER
        else:
            fg, outline = st["fg"], ""
            fill = st["press"] if self._pressed else st["hover"] if self._hover else st["bg"]
        rounded_rect(self, 1, 1, w - 1, h - 1, self._radius, fill=fill, outline=outline)
        self.create_text(w / 2, h / 2, text=self._text, fill=fg, font=ui_font(self._size, True))


class Pill(tk.Canvas):

    def __init__(self, master, text: str = "", fill: str = SURFACE_HI, fg: str = TEXT,
                 size: int = 8, surface: str = SURFACE, padx: int = 10, pady: int = 3):
        super().__init__(master, width=10, height=10, bg=surface, highlightthickness=0, bd=0)
        self._text, self._fill, self._fg = text, fill, fg
        self._size, self._padx, self._pady = size, padx, pady
        self._draw()

    def set(self, text: Optional[str] = None, fill: Optional[str] = None,
            fg: Optional[str] = None) -> None:
        if text is not None:
            self._text = text
        if fill is not None:
            self._fill = fill
        if fg is not None:
            self._fg = fg
        self._draw()

    def _draw(self) -> None:
        font = ui_font(self._size, True)
        w = text_width(self._text, font) + 2 * self._padx
        h = int(self._size * 1.333 * 1.25) + 2 * self._pady
        self.configure(width=w, height=h)
        self.delete("all")
        rounded_rect(self, 1, 1, w - 1, h - 1, (h - 2) / 2, fill=self._fill, outline="")
        self.create_text(w / 2, h / 2, text=self._text, fill=self._fg, font=font)


class ProgressBar(tk.Canvas):

    def __init__(self, master, height: int = 8, color: str = ACCENT,
                 track: str = SURFACE_HI, surface: str = BG):
        super().__init__(master, height=height, bg=surface, highlightthickness=0, bd=0)
        self._h, self._color, self._track = height, color, track
        self._value = 0.0
        self._shown = 0.0
        self._job: Optional[str] = None
        self.bind("<Configure>", lambda _e: self._draw())

    def set_value(self, value: float) -> None:
        self._value = min(max(float(value), 0.0), 1.0)
        if self._job is None:
            self._step()

    def _step(self) -> None:
        diff = self._value - self._shown
        if abs(diff) < 0.004:
            self._shown, self._job = self._value, None
            self._draw()
            return
        self._shown += diff * 0.25
        self._draw()
        self._job = self.after(16, self._step)

    def _draw(self) -> None:
        self.delete("all")
        w = self.winfo_width()
        if w <= 1:
            w = 200
        h = self._h
        rounded_rect(self, 1, 0, w - 1, h, h / 2, fill=self._track, outline="")
        if self._shown > 0:
            fw = max(h, (w - 2) * self._shown)
            color = INNOCENT if self._shown >= 0.999 else self._color
            rounded_rect(self, 1, 0, 1 + fw, h, h / 2, fill=color, outline="")

    def destroy(self) -> None:
        if self._job is not None:
            self.after_cancel(self._job)
            self._job = None
        super().destroy()


class ScrollableFrame(tk.Frame):

    def __init__(self, master, bg: str = SURFACE):
        super().__init__(master, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0, yscrollincrement=20)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview,
                                       style="Dark.Vertical.TScrollbar")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.inner = tk.Frame(self.canvas, bg=bg)
        self._window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>",
                        lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfigure(self._window, width=e.width))
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.bind_all(seq, self._on_wheel, add="+")

    def _on_wheel(self, event) -> None:
        try:
            widget = self.winfo_containing(event.x_root, event.y_root)
        except (KeyError, tk.TclError):
            return
        while widget is not None and widget is not self:
            widget = getattr(widget, "master", None)
        if widget is None:
            return
        if self.inner.winfo_reqheight() <= self.canvas.winfo_height():
            return
        num = getattr(event, "num", None)
        if num == 4:
            step = -1
        elif num == 5:
            step = 1
        else:
            step = -1 if event.delta > 0 else 1
        self.canvas.yview_scroll(step * 2, "units")

    def reveal(self, widget: tk.Misc) -> None:
        self.update_idletasks()
        total = max(self.inner.winfo_reqheight(), 1)
        view_h = self.canvas.winfo_height()
        if total <= view_h:
            return
        top = self.canvas.canvasy(0)
        y, h = widget.winfo_y(), widget.winfo_height()
        if y < top:
            self.canvas.yview_moveto(max(y - 10, 0) / total)
        elif y + h > top + view_h:
            self.canvas.yview_moveto((y + h - view_h + 10) / total)


def draw_avatar(canvas: tk.Canvas, cx: float, cy: float, r: float,
                cell: Optional[Dict[str, Any]]) -> None:
    revealed = bool(cell and cell.get("is_revealed"))
    letter = (str(cell.get("name", "?"))[:1].upper() if cell else "?") or "?"
    size = max(9, int(r * 0.62))
    if revealed:
        accent = status_style(cell)["accent"]
        canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=accent, outline="")
        canvas.create_text(cx, cy, text=letter, fill=INK, font=ui_font(size, True))
    else:
        canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline=DIM, width=2,
                           dash=(4, 3), fill="")
        canvas.create_text(cx, cy, text=letter, fill=MUTED, font=ui_font(size, True))


class CellCard(tk.Canvas):
    PAD = 9
    FLIP_FRAMES = 6
    SHAKE = (-4, 4, -3, 3, -2, 2, -1, 1, 0)

    def __init__(self, master, cell_id: str, callback: Callable[[str], None],
                 cell: Optional[Dict[str, Any]] = None, width: int = 150, height: int = 132):
        super().__init__(master, width=width, height=height, bg=BG,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.cell_id = cell_id
        self.callback = callback
        self.cell = cell
        self.selected = self.highlighted = self.hinted = False
        self._pulse = False
        self._hover = False
        self._xscale = 1.0
        self._dx = 0
        self._pending: Optional[Dict[str, Any]] = None
        self._flip_i = 0
        self._flip_job: Optional[str] = None
        self._shake_i = 0
        self._shake_job: Optional[str] = None

        self.bind("<Button-1>", lambda _e: self.callback(self.cell_id))
        self.bind("<Enter>", lambda _e: self._set_hover(True))
        self.bind("<Leave>", lambda _e: self._set_hover(False))
        self.bind("<Configure>", lambda _e: self.redraw())
        self.redraw()

    def update_cell(self, cell: Dict[str, Any], animate: bool = False) -> None:
        if self._flip_job is not None:
            if cell.get("is_revealed"):
                self._pending = cell     
                return
            self._cancel_flip()
        if (animate and self.cell is not None and cell.get("is_revealed")
                and not self.cell.get("is_revealed")):
            self._pending = cell
            self._flip_i = 0
            self._flip_tick()
            return
        self.cell = cell
        self.redraw()

    def set_flags(self, selected: bool, highlighted: bool, hinted: bool) -> None:
        if (selected, highlighted, hinted) == (self.selected, self.highlighted, self.hinted):
            return
        self.selected, self.highlighted, self.hinted = selected, highlighted, hinted
        self.redraw()

    def set_pulse(self, on: bool) -> None:
        if on != self._pulse:
            self._pulse = on
            if self.hinted:
                self.redraw()

    def _set_hover(self, on: bool) -> None:
        self._hover = on
        self.redraw()

    def _flip_tick(self) -> None:
        n, i = self.FLIP_FRAMES, self._flip_i
        if i < n:
            self._xscale = max(0.04, 1 - (i + 1) / n)
        else:
            if i == n:
                self.cell = self._pending
            self._xscale = min(1.0, (i - n + 1) / n)
        self.redraw()
        self._flip_i += 1
        if self._flip_i >= 2 * n:
            self._xscale, self._flip_job = 1.0, None
            self.redraw()
            return
        self._flip_job = self.after(18, self._flip_tick)

    def _cancel_flip(self) -> None:
        if self._flip_job is not None:
            self.after_cancel(self._flip_job)
        self._flip_job, self._xscale = None, 1.0

    def shake(self) -> None:
        if self._shake_job is not None:
            self.after_cancel(self._shake_job)
        self._shake_i = 0
        self._shake_tick()

    def _shake_tick(self) -> None:
        if self._shake_i >= len(self.SHAKE):
            self._dx, self._shake_job = 0, None
            self.redraw()
            return
        self._dx = self.SHAKE[self._shake_i]
        self._shake_i += 1
        self.redraw()
        self._shake_job = self.after(28, self._shake_tick)

    def destroy(self) -> None:
        for job in (self._flip_job, self._shake_job):
            if job is not None:
                self.after_cancel(job)
        self._flip_job = self._shake_job = None
        super().destroy()

    def redraw(self) -> None:
        self.delete("all")
        cell = self.cell
        if not cell:
            return
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 1 or h <= 1:
            w, h = int(self.cget("width")), int(self.cget("height"))

        pad = self.PAD
        style = status_style(cell)
        revealed = bool(cell.get("is_revealed"))
        half = max((w / 2 - pad) * self._xscale, 2)
        cx = w / 2 + self._dx
        x1, x2 = cx - half, cx + half
        y1, y2 = pad, h - pad
        r = min(16, half, (y2 - y1) / 2)

        if self.hinted:
            ring = HINT if self._pulse else mix(HINT, BG, 0.55)
            rounded_rect(self, x1 - 4, y1 - 4, x2 + 4, y2 + 4, r + 4, fill="", outline=ring, width=2)
        elif self.highlighted:
            rounded_rect(self, x1 - 4, y1 - 4, x2 + 4, y2 + 4, r + 4, fill="", outline=ACCENT, width=2)

        fill, edge, edge_w = style["fill"], style["edge"], 2 if revealed else 1
        if not revealed:
            if self.highlighted:
                fill = mix(fill, ACCENT, 0.14)
            if self._hover:
                fill, edge = mix(fill, TEXT, 0.06), DIM
        if self.selected:
            edge, edge_w = TEXT, 3
        rounded_rect(self, x1, y1, x2, y2, r, fill=fill, outline=edge, width=edge_w)

        if self._xscale < 0.72:  
            return

        vw, vh = x2 - x1, y2 - y1
        name_pt = max(9, min(14, round(vh / 11)))
        tag_pt = max(7, name_pt - 3)
        compact = vh < 100

        self.create_text(x1 + 14, y1 + 14, text=cell["id"], anchor="w", fill=MUTED,
                         font=ui_font(tag_pt, True))
        dot_x, dot_y = x2 - 16, y1 + 14
        if revealed:
            self.create_oval(dot_x - 4, dot_y - 4, dot_x + 4, dot_y + 4, fill=style["edge"], outline="")
        else:
            self.create_oval(dot_x - 4, dot_y - 4, dot_x + 4, dot_y + 4, outline=DIM, width=1.5)

        if compact:
            name_y, prof_y, pill_y = y1 + vh * 0.38, y1 + vh * 0.58, y1 + vh * 0.80
        else:
            draw_avatar(self, cx, y1 + vh * 0.34, min(vw, vh) * 0.17, cell)
            name_y, prof_y, pill_y = y1 + vh * 0.63, y1 + vh * 0.76, y1 + vh * 0.90

        self.create_text(cx, name_y, text=cell["name"], fill=TEXT,
                         font=fit_font(cell["name"], name_pt, True, vw - 18))
        self.create_text(cx, prof_y, text=cell["profession"], fill=MUTED,
                         font=fit_font(cell["profession"], max(8, name_pt - 2), False, vw - 18))

        label, pfont = style["label"], ui_font(tag_pt, True)
        pw = text_width(label, pfont) + 20
        ph = int(tag_pt * 1.333 * 1.35) + 4
        rounded_rect(self, cx - pw / 2, pill_y - ph / 2, cx + pw / 2, pill_y + ph / 2, ph / 2,
                     fill=style["pill"], outline="")
        self.create_text(cx, pill_y, text=label, fill=style["pill_fg"], font=pfont)


class BoardPanel(tk.Frame):

    ASPECT = 1.12
    MIN_H, MAX_H = 84, 170

    def __init__(self, master, engine, select_callback: Callable[[str], None]):
        super().__init__(master, bg=BG)
        self.engine = engine
        self.select_callback = select_callback
        self.cells: Dict[str, CellCard] = {}
        self._card_size = (0, 0)
        self._selected: Optional[str] = None
        self._highlighted: set = set()
        self._hint: Optional[str] = None
        self._pulse_on = False
        self._pulse_job: Optional[str] = None

        self._grid = tk.Frame(self, bg=BG)
        self._grid.place(relx=0.5, rely=0.5, anchor="center")
        self.bind("<Configure>", lambda e: self._fit(e.width, e.height))
        self.rebuild()

    def rebuild(self) -> None:
        self._stop_pulse()
        self._hint = None
        for child in self._grid.winfo_children():
            child.destroy()
        self.cells.clear()

        state = self.engine.state
        label_font = ui_font(10, True)
        for c in range(state.size):
            tk.Label(self._grid, text=chr(ord("A") + c), bg=BG, fg=DIM,
                     font=label_font).grid(row=0, column=c + 1)
        for r in range(state.size):
            tk.Label(self._grid, text=str(r + 1), bg=BG, fg=DIM, font=label_font,
                     width=2).grid(row=r + 1, column=0)

        for cid, cell in state.board.items():
            col = ord(str(cell.get("col", cid[0])).upper()) - ord("A")
            row = int(cell.get("row", cid[1:])) - 1
            card = CellCard(self._grid, cid, self.select_callback, cell=cell)
            card.grid(row=row + 1, column=col + 1)
            self.cells[cid] = card

        self._card_size = (0, 0)
        self._fit()
        self._push_flags()

    def _fit(self, w: Optional[int] = None, h: Optional[int] = None) -> None:
        w = w or self.winfo_width()
        h = h or self.winfo_height()
        if w <= 1 or h <= 1:
            return
        size = max(self.engine.state.size, 1)
        avail_h = h - 40 - 24
        avail_w = w - 40 - 28
        ch = min(avail_h / size, avail_w / size / self.ASPECT)
        ch = int(max(self.MIN_H, min(ch, self.MAX_H)))
        cw = int(ch * self.ASPECT)
        if (cw, ch) == self._card_size:
            return
        self._card_size = (cw, ch)
        for card in self.cells.values():
            card.configure(width=cw, height=ch)

    def refresh(self, animate: Optional[str] = None) -> None:
        board = self.engine.state.board
        if set(board) != set(self.cells):
            self.rebuild()
        for cid, cell in board.items():
            self.cells[cid].update_cell(cell, animate=(cid == animate))
        self._push_flags()

    def set_view(self, selected: Optional[str] = None, highlighted: Iterable[str] = (),
                 hint: Optional[str] = None) -> None:
        self._selected = selected
        self._highlighted = set(highlighted or ())
        if hint != self._hint:
            self._stop_pulse()
            self._hint = hint
            if hint:
                self._pulse_on = True
                self._pulse_tick()
        self._push_flags()

    def _push_flags(self) -> None:
        for cid, card in self.cells.items():
            card.set_flags(cid == self._selected, cid in self._highlighted, cid == self._hint)

    def shake(self, cid: str) -> None:
        card = self.cells.get(cid)
        if card is not None:
            card.shake()

    def _pulse_tick(self) -> None:
        card = self.cells.get(self._hint) if self._hint else None
        if card is None:
            self._pulse_job = None
            return
        card.set_pulse(self._pulse_on)
        self._pulse_on = not self._pulse_on
        self._pulse_job = self.after(520, self._pulse_tick)

    def _stop_pulse(self) -> None:
        if self._pulse_job is not None:
            self.after_cancel(self._pulse_job)
            self._pulse_job = None
        for card in self.cells.values():
            card.set_pulse(False)

    def destroy(self) -> None:
        self._stop_pulse()
        super().destroy()


def _panel(master, **kw) -> tk.Frame:
    return tk.Frame(master, bg=SURFACE, highlightthickness=1,
                    highlightbackground=BORDER, highlightcolor=BORDER, **kw)


class InfoPanel(tk.Frame):
    PAD = 16

    def __init__(self, master, on_verdict: Callable[[str], None]):
        super().__init__(master, bg=SURFACE, highlightthickness=1,
                         highlightbackground=BORDER, highlightcolor=BORDER)
        self.on_verdict = on_verdict
        pad = self.PAD

        tk.Label(self, text="Suspect file", bg=SURFACE, fg=MUTED, anchor="w",
                 font=ui_font(10, True)).pack(fill="x", padx=pad, pady=(14, 10))

        row = tk.Frame(self, bg=SURFACE)
        row.pack(fill="x", padx=pad)
        self.avatar = tk.Canvas(row, width=60, height=60, bg=SURFACE, highlightthickness=0)
        self.avatar.pack(side="left")
        col = tk.Frame(row, bg=SURFACE)
        col.pack(side="left", fill="x", expand=True, padx=(14, 0))
        self.name = tk.Label(col, text="", bg=SURFACE, fg=TEXT, anchor="w", font=ui_font(17, True))
        self.name.pack(fill="x")
        meta = tk.Frame(col, bg=SURFACE)
        meta.pack(fill="x", pady=(5, 0))
        self.profession = tk.Label(meta, text="", bg=SURFACE, fg=MUTED, font=ui_font(10))
        self.profession.pack(side="left")
        self.id_pill = Pill(meta, "", fill=SURFACE_HI, fg=MUTED, surface=SURFACE)
        self.id_pill.pack(side="left", padx=(10, 0))
        self.status_pill = Pill(meta, "", surface=SURFACE)
        self.status_pill.pack(side="left", padx=(6, 0))

        tk.Frame(self, height=1, bg=BORDER).pack(fill="x", padx=pad, pady=(16, 12))

        clue_row = tk.Frame(self, bg=SURFACE, height=24)
        clue_row.pack(fill="x", padx=pad)
        clue_row.pack_propagate(False)
        tk.Label(clue_row, text="Clue", bg=SURFACE, fg=MUTED, font=ui_font(10, True)).pack(side="left")
        self.clue_tag = Pill(clue_row, "", fill=SURFACE_HI, fg=ACCENT, surface=SURFACE)
        self._clue_tag_visible = False

        self.clue_text = tk.Label(self, text="", bg=SURFACE, fg=TEXT, justify="left", anchor="w",
                                  font=ui_font(11), wraplength=320)
        self.clue_text.pack(fill="x", padx=pad, pady=(6, 0))
        auto_wrap(self.clue_text, self, margin=2 * pad + 4, minimum=120)

        actions = tk.Frame(self, bg=SURFACE)
        actions.pack(fill="x", padx=pad, pady=(18, 16))
        actions.grid_columnconfigure(0, weight=1, uniform="verdict")
        actions.grid_columnconfigure(1, weight=1, uniform="verdict")
        self.btn_criminal = RoundedButton(actions, "Criminal", lambda: self.on_verdict(STATUS_CRIMINAL),
                                          style="danger", height=42, surface=SURFACE)
        self.btn_innocent = RoundedButton(actions, "Innocent", lambda: self.on_verdict(STATUS_INNOCENT),
                                          style="success", height=42, surface=SURFACE)
        self.btn_criminal.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.btn_innocent.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        self.show_cell(None)

    def _set_clue_tag(self, text: Optional[str]) -> None:
        if text:
            self.clue_tag.set(text)
            if not self._clue_tag_visible:
                self.clue_tag.pack(side="right")
                self._clue_tag_visible = True
        elif self._clue_tag_visible:
            self.clue_tag.pack_forget()
            self._clue_tag_visible = False

    def show_cell(self, cell: Optional[Dict[str, Any]], locked: bool = False) -> None:
        self.avatar.delete("all")
        if not cell:
            draw_avatar(self.avatar, 30, 30, 26, None)
            self.name.configure(text="No suspect selected")
            self.profession.configure(text="Click a card on the board")
            self.id_pill.pack_forget()
            self.status_pill.pack_forget()
            self._set_clue_tag(None)
            self.clue_text.configure(
                text="A suspect's clue stays sealed until you rule on them. "
                     "Pick someone the revealed clues already prove.",
                fg=MUTED)
            self.btn_criminal.set_enabled(False)
            self.btn_innocent.set_enabled(False)
            return

        style = status_style(cell)
        revealed = bool(cell.get("is_revealed"))
        draw_avatar(self.avatar, 30, 30, 26, cell)
        self.name.configure(text=cell.get("name", ""))
        self.profession.configure(text=cell.get("profession", ""))
        self.id_pill.set(cell.get("id", ""))
        self.status_pill.set(style["label"], fill=style["pill"], fg=style["pill_fg"])
        self.id_pill.pack(side="left", padx=(10, 0))
        self.status_pill.pack(side="left", padx=(6, 0))

        clue = cell.get("clue")
        if revealed and clue:
            self._set_clue_tag(clue_label(clue))
            self.clue_text.configure(text=clue.get("text", ""), fg=TEXT)
        elif revealed:
            self._set_clue_tag(None)
            self.clue_text.configure(text="This suspect carried no clue.", fg=MUTED)
        else:
            self._set_clue_tag(None)
            self.clue_text.configure(
                text="Sealed. Rule on this suspect to reveal what they know.", fg=MUTED)

        can_rule = (not revealed) and (not locked)
        self.btn_criminal.set_enabled(can_rule)
        self.btn_innocent.set_enabled(can_rule)


class ClueCard(tk.Frame):

    def __init__(self, master, clue: Dict[str, Any], owner_cell: Optional[Dict[str, Any]],
                 on_click: Callable[[str], None], is_new: bool = False):
        super().__init__(master, bg=SURFACE_HI, highlightthickness=1,
                         highlightbackground=BORDER, cursor="hand2")
        self.owner = str(clue.get("owner", ""))
        style = status_style(owner_cell)
        tk.Frame(self, width=4, bg=style["accent"]).pack(side="left", fill="y")
        body = tk.Frame(self, bg=SURFACE_HI)
        body.pack(side="left", fill="both", expand=True, padx=12, pady=10)

        top = tk.Frame(body, bg=SURFACE_HI)
        top.pack(fill="x")
        name = (owner_cell or {}).get("name", self.owner)
        tk.Label(top, text=name, bg=SURFACE_HI, fg=TEXT, font=ui_font(11, True)).pack(side="left")
        tk.Label(top, text=self.owner, bg=SURFACE_HI, fg=MUTED,
                 font=ui_font(9)).pack(side="left", padx=(8, 0))
        Pill(top, clue_label(clue), fill=SURFACE, fg=ACCENT, surface=SURFACE_HI).pack(side="right")
        if is_new:
            Pill(top, "New", fill=ACCENT, fg=INK, surface=SURFACE_HI).pack(side="right", padx=(0, 6))

        text = tk.Label(body, text=clue.get("text", ""), bg=SURFACE_HI, fg="#302B28", justify="left",
                        anchor="w", font=ui_font(10), wraplength=300)
        text.pack(fill="x", pady=(8, 0))
        auto_wrap(text, body, margin=4, minimum=100)

        bind_tree(self, "<Button-1>", lambda _e: on_click(self.owner))
        bind_tree(self, "<Enter>", lambda _e: self._hover(True))
        bind_tree(self, "<Leave>", lambda _e: self._hover(False))
        self._active = False

    def _hover(self, on: bool) -> None:
        if self._active:
            return
        if not on: 
            try:
                widget = self.winfo_containing(*self.winfo_pointerxy())
            except (KeyError, tk.TclError):
                widget = None
            while widget is not None:
                if widget is self:
                    return
                widget = getattr(widget, "master", None)
        self.configure(highlightbackground=DIM if on else BORDER)

    def set_active(self, active: bool) -> None:
        self._active = active
        self.configure(highlightbackground=ACCENT if active else BORDER,
                       highlightthickness=2 if active else 1)


class CluePanel(tk.Frame):

    def __init__(self, master, on_select: Callable[[str], None]):
        super().__init__(master, bg=SURFACE)
        self.on_select = on_select
        self.scroll = ScrollableFrame(self, bg=SURFACE)
        self.scroll.pack(fill="both", expand=True)
        self._cards: Dict[str, ClueCard] = {}
        self._signature: Any = None

    def update_clues(self, clues: List[Dict[str, Any]], board: Dict[str, Dict[str, Any]],
                     newest_owner: Optional[str] = None) -> None:
        signature = (tuple(str(c.get("owner")) for c in clues), newest_owner)
        if signature == self._signature:
            return
        self._signature = signature
        for child in self.scroll.inner.winfo_children():
            child.destroy()
        self._cards.clear()

        if not clues:
            tk.Label(self.scroll.inner, text="No clues yet.\nRule on a suspect to reveal theirs.",
                     bg=SURFACE, fg=MUTED, font=ui_font(10), justify="center").pack(pady=40)
            return
        for clue in reversed(clues):
            owner = str(clue.get("owner", ""))
            card = ClueCard(self.scroll.inner, clue, board.get(owner), self.on_select,
                            is_new=(owner == newest_owner))
            card.pack(fill="x", padx=10, pady=(10, 0))
            self._cards[owner] = card
        tk.Frame(self.scroll.inner, height=10, bg=SURFACE).pack()

    def set_active(self, owner: Optional[str]) -> None:
        for oid, card in self._cards.items():
            card.set_active(oid == owner)
        if owner in self._cards:
            self.scroll.reveal(self._cards[owner])


class HistoryPanel(tk.Frame):

    KIND_COLOR = {"success": INNOCENT, "warn": HINT, "error": CRIMINAL, "info": ACCENT, "hint": HINT}

    def __init__(self, master):
        super().__init__(master, bg=SURFACE)
        self.scroll = ScrollableFrame(self, bg=SURFACE)
        self.scroll.pack(fill="both", expand=True)
        self._entries: List[tk.Frame] = []
        self._empty: Optional[tk.Label] = None
        self._show_empty()

    def _show_empty(self) -> None:
        self._empty = tk.Label(self.scroll.inner, text="Your rulings and hints will appear here.",
                               bg=SURFACE, fg=MUTED, font=ui_font(10))
        self._empty.pack(pady=40)

    def add(self, kind: str, title: str, message: str, step: str = "") -> None:
        if self._empty is not None:
            self._empty.destroy()
            self._empty = None
        color = self.KIND_COLOR.get(kind, ACCENT)
        card = tk.Frame(self.scroll.inner, bg=SURFACE_HI, highlightthickness=1,
                        highlightbackground=BORDER)
        tk.Frame(card, width=4, bg=color).pack(side="left", fill="y")
        body = tk.Frame(card, bg=SURFACE_HI)
        body.pack(side="left", fill="both", expand=True, padx=12, pady=10)
        top = tk.Frame(body, bg=SURFACE_HI)
        top.pack(fill="x")
        tk.Label(top, text=title, bg=SURFACE_HI, fg=color, font=ui_font(10, True)).pack(side="left")
        if step:
            tk.Label(top, text=step, bg=SURFACE_HI, fg=MUTED, font=ui_font(9)).pack(side="right")
        text = tk.Label(body, text=message, bg=SURFACE_HI, fg="#302B28", justify="left", anchor="w",
                        font=ui_font(10), wraplength=300)
        text.pack(fill="x", pady=(6, 0))
        auto_wrap(text, body, margin=4, minimum=100)

        if self._entries:
            card.pack(fill="x", padx=10, pady=(10, 0), before=self._entries[0])
        else:
            card.pack(fill="x", padx=10, pady=(10, 0))
        self._entries.insert(0, card)
        self.scroll.canvas.yview_moveto(0)

    @property
    def count(self) -> int:
        return len(self._entries)

    def clear(self) -> None:
        for child in self.scroll.inner.winfo_children():
            child.destroy()
        self._entries.clear()
        self._empty = None
        self._show_empty()


class SolverPanel(tk.Frame):

    TILES = (("sat_calls", "SAT calls"), ("decisions", "Decisions"),
             ("propagations", "Propagations"), ("backtracks", "Backtracks"))
    FACTS = (("clues", "Clues in the knowledge base"), ("verdicts", "Verdicts proven"),
             ("hidden", "Suspects still hidden"), ("runtime", "Solver time"),
             ("primary_variables", "Primary variables (peak)"),
             ("auxiliary_variables", "Auxiliary variables (peak)"),
             ("clauses", "CNF clauses (peak)"))

    def __init__(self, master):
        super().__init__(master, bg=SURFACE)
        self.scroll = ScrollableFrame(self, bg=SURFACE)
        self.scroll.pack(fill="both", expand=True)
        body = self.scroll.inner

        intro = tk.Label(body, text="Every ruling is checked by the SAT solver. A verdict passes only "
                                    "when the revealed clues prove it, so guessing is rejected.",
                         bg=SURFACE, fg=MUTED, justify="left", anchor="w", font=ui_font(10),
                         wraplength=320)
        intro.pack(fill="x", padx=14, pady=(14, 12))
        auto_wrap(intro, body, margin=28, minimum=120)

        grid = tk.Frame(body, bg=SURFACE)
        grid.pack(fill="x", padx=14)
        grid.grid_columnconfigure(0, weight=1, uniform="tile")
        grid.grid_columnconfigure(1, weight=1, uniform="tile")
        self._values: Dict[str, tk.Label] = {}
        for i, (key, caption) in enumerate(self.TILES):
            tile = tk.Frame(grid, bg=SURFACE_HI, highlightthickness=1, highlightbackground=BORDER)
            tile.grid(row=i // 2, column=i % 2, sticky="ew",
                      padx=(0, 5) if i % 2 == 0 else (5, 0), pady=(0, 10))
            value = tk.Label(tile, text="0", bg=SURFACE_HI, fg=TEXT, anchor="w", font=ui_font(20, True))
            value.pack(fill="x", padx=12, pady=(10, 0))
            tk.Label(tile, text=caption, bg=SURFACE_HI, fg=MUTED, anchor="w",
                     font=ui_font(9)).pack(fill="x", padx=12, pady=(0, 10))
            self._values[key] = value

        facts = tk.Frame(body, bg=SURFACE)
        facts.pack(fill="x", padx=14, pady=(4, 14))
        for key, caption in self.FACTS:
            row = tk.Frame(facts, bg=SURFACE)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=caption, bg=SURFACE, fg=MUTED, font=ui_font(10)).pack(side="left")
            value = tk.Label(row, text="0", bg=SURFACE, fg=TEXT, font=ui_font(10, True))
            value.pack(side="right")
            self._values[key] = value

    def update_stats(self, data: Dict[str, Any]) -> None:
        for key, label in self._values.items():
            if key not in data:
                continue
            value = data[key]
            if value is None:
                text = "-"
            elif key == "runtime":
                text = f"{float(value) * 1000:.1f} ms"
            else:
                text = f"{int(value):,}"
            label.configure(text=text)


class TabView(tk.Frame):

    def __init__(self, master):
        super().__init__(master, bg=BG)
        self._bar = tk.Frame(self, bg=SURFACE, highlightthickness=1, highlightbackground=BORDER)
        self._bar.pack(fill="x")
        self._body = tk.Frame(self, bg=SURFACE, highlightthickness=1, highlightbackground=BORDER)
        self._body.pack(fill="both", expand=True, pady=(8, 0))
        self._tabs: Dict[str, Dict[str, Any]] = {}
        self._current: Optional[str] = None

    def add(self, name: str) -> tk.Frame:
        page = tk.Frame(self._body, bg=SURFACE)
        label = tk.Label(self._bar, text=name, bg=SURFACE, fg=MUTED, padx=13, pady=9,
                         font=ui_font(10, True), cursor="hand2")
        label.pack(side="left")
        label.bind("<Button-1>", lambda _e, n=name: self.select(n))
        self._tabs[name] = {"label": label, "page": page}
        if self._current is None:
            self.select(name)
        return page

    def select(self, name: str) -> None:
        if name == self._current or name not in self._tabs:
            return
        if self._current is not None:
            old = self._tabs[self._current]
            old["page"].pack_forget()
            old["label"].configure(bg=SURFACE, fg=MUTED)
        cur = self._tabs[name]
        cur["page"].pack(fill="both", expand=True)
        cur["label"].configure(bg=SURFACE_HI, fg=TEXT)
        self._current = name

    def set_badge(self, name: str, count: int) -> None:
        if name in self._tabs:
            self._tabs[name]["label"].configure(text=f"{name}  {count}" if count else name)


class SpeedControl(tk.Frame):
    OPTIONS = ("Slow", "Normal", "Fast")

    def __init__(self, master, default: str = "Normal"):
        super().__init__(master, bg=SURFACE, highlightthickness=1, highlightbackground=BORDER)
        self._labels: Dict[str, tk.Label] = {}
        self._value = default
        for name in self.OPTIONS:
            label = tk.Label(self, text=name, bg=SURFACE, fg=MUTED, padx=11, pady=7,
                             font=ui_font(9, True), cursor="hand2")
            label.pack(side="left")
            label.bind("<Button-1>", lambda _e, n=name: self.set(n))
            self._labels[name] = label
        self.set(default)

    def set(self, name: str) -> None:
        if name not in self._labels:
            return
        self._value = name
        for key, label in self._labels.items():
            active = key == name
            label.configure(bg=SURFACE_HI if active else SURFACE, fg=TEXT if active else MUTED)

    def get(self) -> str:
        return self._value


class TracePanel(tk.Frame):

    STATE_STYLE = {
        "IDLE": ("Idle", SURFACE_HI, MUTED),
        "RUNNING": ("Running", ACCENT, INK),
        "SOLVED": ("Solved", INNOCENT, INK),
        "STUCK": ("Stuck", HINT, INK),
        "STOPPED": ("Stopped", SURFACE_HI, TEXT),
        "INCONSISTENT": ("Inconsistent", CRIMINAL, INK),
        "REJECTED": ("Rejected", CRIMINAL, INK),
        "TIMEOUT": ("Timeout", CRIMINAL, INK),
        "ERROR": ("Error", CRIMINAL, INK),
    }
    IDLE_TEXT = ("Press Auto solve to record the deduction trace: step, active clues, "
                 "SAT queries, verdict and the clue each verdict reveals.")

    def __init__(self, master, on_select: Callable[[str], None], on_export: Callable[[], None]):
        super().__init__(master, bg=SURFACE)
        self.on_select = on_select

        head = tk.Frame(self, bg=SURFACE)
        head.pack(fill="x", padx=14, pady=(14, 0))
        self.state_pill = Pill(head, "Idle", fill=SURFACE_HI, fg=MUTED, surface=SURFACE)
        self.state_pill.pack(side="left")
        RoundedButton(head, "Export JSON", on_export, width=104, height=28, radius=9, size=9,
                      surface=SURFACE).pack(side="right")

        self.summary = tk.Label(self, text=self.IDLE_TEXT, bg=SURFACE, fg=MUTED, justify="left",
                                anchor="w", font=ui_font(10), wraplength=320)
        self.summary.pack(fill="x", padx=14, pady=(8, 12))
        auto_wrap(self.summary, self, margin=28, minimum=120)
        tk.Frame(self, height=1, bg=BORDER).pack(fill="x")

        self.scroll = ScrollableFrame(self, bg=SURFACE)
        self.scroll.pack(fill="both", expand=True)
        self._entries: List[tk.Frame] = []

    @property
    def count(self) -> int:
        return len(self._entries)

    def clear(self) -> None:
        for child in self.scroll.inner.winfo_children():
            child.destroy()
        self._entries.clear()
        self.set_state("IDLE", self.IDLE_TEXT)

    def set_state(self, key: str, text: str) -> None:
        label, fill, fg = self.STATE_STYLE.get(key, self.STATE_STYLE["IDLE"])
        self.state_pill.set(label, fill=fill, fg=fg)
        self.summary.configure(text=text)

    def add_step(self, entry: Dict[str, Any], name: str) -> None:
        verdict = entry.get("verdict")
        style = STATUS_STYLE.get(verdict, STATUS_STYLE[STATUS_UNKNOWN])
        cid = str(entry.get("character", ""))

        card = tk.Frame(self.scroll.inner, bg=SURFACE_HI, highlightthickness=1,
                        highlightbackground=BORDER, cursor="hand2")
        tk.Frame(card, width=4, bg=style["accent"]).pack(side="left", fill="y")
        body = tk.Frame(card, bg=SURFACE_HI)
        body.pack(side="left", fill="both", expand=True, padx=12, pady=10)

        top = tk.Frame(body, bg=SURFACE_HI)
        top.pack(fill="x")
        tk.Label(top, text=f"Step {entry.get('step', '?')}", bg=SURFACE_HI, fg=MUTED,
                 font=ui_font(9, True)).pack(side="left")
        tk.Label(top, text=f"Wave {entry.get('wave', '?')}", bg=SURFACE_HI, fg=MUTED,
                 font=ui_font(9)).pack(side="right")

        who = tk.Frame(body, bg=SURFACE_HI)
        who.pack(fill="x", pady=(6, 0))
        tk.Label(who, text=name, bg=SURFACE_HI, fg=TEXT, font=ui_font(12, True)).pack(side="left")
        tk.Label(who, text=cid, bg=SURFACE_HI, fg=MUTED, font=ui_font(9)).pack(side="left", padx=(8, 0))
        Pill(who, style["label"], fill=style["pill"], fg=style["pill_fg"],
             surface=SURFACE_HI).pack(side="right")

        clue_text = entry.get("revealed_clue_text")
        if clue_text:
            reveal = tk.Label(body, text=f"Revealed: {clue_text}", bg=SURFACE_HI, fg="#302B28",
                              justify="left", anchor="w", font=ui_font(10), wraplength=300)
            reveal.pack(fill="x", pady=(8, 0))
            auto_wrap(reveal, body, margin=4, minimum=100)

        for query in entry.get("sat_queries") or []:
            row = tk.Frame(body, bg=SURFACE_HI)
            row.pack(fill="x", pady=(6, 0))
            tk.Label(row, text=str(query.get("query", "")), bg=SURFACE_HI, fg=MUTED,
                     font=ui_font(9)).pack(side="left")
            sat = bool(query.get("sat"))
            Pill(row, "SAT" if sat else "UNSAT", fill=SURFACE if sat else INNOCENT,
                 fg=MUTED if sat else INK, size=7, surface=SURFACE_HI, padx=8, pady=2).pack(side="right")

        active = entry.get("active_clue_ids") or []
        tk.Label(body, text=f"{len(active)} active clues", bg=SURFACE_HI, fg=DIM,
                 font=ui_font(9)).pack(anchor="w", pady=(8, 0))

        bind_tree(card, "<Button-1>", lambda _e: self.on_select(cid))
        if self._entries:
            card.pack(fill="x", padx=10, pady=(10, 0), before=self._entries[0])
        else:
            card.pack(fill="x", padx=10, pady=(10, 0))
        self._entries.insert(0, card)
        self.scroll.canvas.yview_moveto(0)


class Logo(tk.Canvas):

    PATTERN = ((0, 2, 0), (1, 0, 0), (0, 0, 1))

    def __init__(self, master, size: int = 36):
        super().__init__(master, width=size, height=size, bg=BG, highlightthickness=0, bd=0)
        cell, gap = (size - 2 * 3) / 3, 3
        for r, row in enumerate(self.PATTERN):
            for c, kind in enumerate(row):
                x, y = c * (cell + gap), r * (cell + gap)
                if kind == 2:
                    rounded_rect(self, x, y, x + cell, y + cell, 3, fill=CRIMINAL, outline="")
                elif kind == 1:
                    rounded_rect(self, x, y, x + cell, y + cell, 3, fill=INNOCENT, outline="")
                else:
                    rounded_rect(self, x, y, x + cell, y + cell, 3, fill=SURFACE_HI, outline=BORDER)


class HeaderBar(tk.Frame):
    def __init__(self, master, on_load: Callable[[], None], on_restart: Callable[[], None],
                 on_hint: Callable[[], None], on_auto: Callable[[], None]):
        super().__init__(master, bg=BG)
        inner = tk.Frame(self, bg=BG)
        inner.pack(fill="x", padx=24, pady=(16, 14))

        Logo(inner).pack(side="left")
        titles = tk.Frame(inner, bg=BG)
        titles.pack(side="left", padx=(14, 0))
        tk.Label(titles, text="Griductive", bg=BG, fg=TEXT, font=ui_font(19, True)).pack(anchor="w")
        tk.Label(titles, text="Rule on every suspect. No guessing.", bg=BG, fg=MUTED,
                 font=ui_font(9)).pack(anchor="w")

        self.auto_button = RoundedButton(inner, "Auto solve", on_auto, style="primary", width=116, height=38)
        self.auto_button.pack(side="right")
        self.hint_button = RoundedButton(inner, "Hint", on_hint, width=84, height=38)
        self.hint_button.pack(side="right", padx=(0, 10))
        RoundedButton(inner, "Restart", on_restart, width=96, height=38).pack(side="right", padx=(0, 10))
        RoundedButton(inner, "Load puzzle", on_load, width=116, height=38).pack(side="right", padx=(0, 10))
        self.speed = SpeedControl(inner)
        self.speed.pack(side="right", padx=(0, 20))
        tk.Label(inner, text="Auto speed", bg=BG, fg=MUTED, font=ui_font(9)).pack(side="right", padx=(0, 8))

        tk.Frame(self, height=1, bg=BORDER).pack(fill="x")

    def set_hint_enabled(self, enabled: bool) -> None:
        self.hint_button.set_enabled(enabled)

    def set_auto_state(self, running: bool, enabled: bool = True) -> None:
        self.auto_button.set_text("Stop" if running else "Auto solve")
        self.auto_button.set_style("danger" if running else "primary")
        self.auto_button.set_enabled(enabled)


class ProgressStrip(tk.Frame):

    def __init__(self, master):
        super().__init__(master, bg=BG)
        row = tk.Frame(self, bg=BG)
        row.pack(fill="x")
        self.solved = tk.Label(row, text="0 of 0", bg=BG, fg=TEXT, font=ui_font(14, True))
        self.solved.pack(side="left")
        tk.Label(row, text="suspects ruled", bg=BG, fg=MUTED, font=ui_font(10)).pack(
            side="left", padx=(8, 0), pady=(3, 0))
        self.turn = tk.Label(row, text="Turn 0", bg=BG, fg=MUTED, font=ui_font(10, True))
        self.turn.pack(side="right")
        self.bar = ProgressBar(self, height=8)
        self.bar.pack(fill="x", pady=(10, 0))

    def update_progress(self, solved: int, total: int, turn: int, fraction: float) -> None:
        self.solved.configure(text=f"{solved} of {total}")
        self.turn.configure(text=f"Turn {turn}")
        self.bar.set_value(fraction)


class Legend(tk.Frame):
    ITEMS = (("Unknown", MUTED, "ring"), ("Criminal", CRIMINAL, "fill"),
             ("Innocent", INNOCENT, "fill"), ("Clue region", ACCENT, "ring"), ("Hint", HINT, "ring"))

    def __init__(self, master):
        super().__init__(master, bg=BG)
        for label, color, mode in self.ITEMS:
            swatch = tk.Canvas(self, width=16, height=16, bg=BG, highlightthickness=0, bd=0)
            if mode == "fill":
                rounded_rect(swatch, 1, 1, 15, 15, 5, fill=color, outline="")
            else:
                rounded_rect(swatch, 2, 2, 14, 14, 5, fill="", outline=color, width=2)
            swatch.pack(side="left")
            tk.Label(self, text=label, bg=BG, fg=MUTED, font=ui_font(9)).pack(side="left", padx=(6, 18))


class StatusBar(tk.Frame):

    KINDS = {"info": ACCENT, "success": INNOCENT, "warn": HINT, "error": CRIMINAL, "hint": HINT}
    SHORTCUTS = "Arrows move   C criminal   I innocent   H hint   A auto solve   Esc clear"

    def __init__(self, master):
        super().__init__(master, bg=SURFACE)
        tk.Frame(self, height=1, bg=BORDER).pack(fill="x")
        row = tk.Frame(self, bg=SURFACE)
        row.pack(fill="x", padx=24, pady=9)
        self.dot = tk.Canvas(row, width=12, height=12, bg=SURFACE, highlightthickness=0, bd=0)
        self.dot.pack(side="left")
        self._dot_item = self.dot.create_oval(2, 2, 10, 10, fill=ACCENT, outline="")
        self.label = tk.Label(row, text="Ready", bg=SURFACE, fg=TEXT, anchor="w", font=ui_font(10))
        self.label.pack(side="left", padx=(10, 0))
        tk.Label(row, text=self.SHORTCUTS, bg=SURFACE, fg=DIM, font=ui_font(9)).pack(side="right")

    def set(self, text: str, kind: str = "info") -> None:
        self.dot.itemconfigure(self._dot_item, fill=self.KINDS.get(kind, ACCENT))
        self.label.configure(text=text)


class VictoryOverlay(tk.Frame):

    def __init__(self, master, on_restart: Callable[[], None]):
        super().__init__(master, bg=SURFACE, highlightthickness=2,
                         highlightbackground=INNOCENT, highlightcolor=INNOCENT)
        tk.Label(self, text="Case closed", bg=SURFACE, fg=INNOCENT,
                 font=ui_font(24, True)).pack(padx=48, pady=(28, 6))
        self.summary = tk.Label(self, text="", bg=SURFACE, fg=TEXT, font=ui_font(11))
        self.summary.pack(padx=48)
        row = tk.Frame(self, bg=SURFACE)
        row.pack(pady=(22, 26))
        RoundedButton(row, "Play again", on_restart, style="primary", width=120, height=40,
                      surface=SURFACE).pack(side="left", padx=(0, 10))
        RoundedButton(row, "Review board", self.hide, width=130, height=40,
                      surface=SURFACE).pack(side="left")

    def show(self, total: int, turns: int) -> None:
        self.summary.configure(text=f"All {total} suspects ruled in {turns} moves, no guesses.")
        self.place(relx=0.5, rely=0.5, anchor="center")
        self.lift()

    def hide(self) -> None:
        self.place_forget()

DIFFICULTY_COLOR = {"easy": INNOCENT, "medium": HINT, "hard": CRIMINAL}


class LevelCard(tk.Canvas):

    W, H = 164, 152

    def __init__(self, master, info: Dict[str, Any], on_pick: Callable[[Dict[str, Any]], None],
                 current: bool = False, solved: bool = False):
        broken = bool(info.get("error"))
        super().__init__(master, width=self.W, height=self.H, bg=BG, highlightthickness=0, bd=0,
                         cursor="arrow" if broken else "hand2")
        self.info, self.on_pick = info, on_pick
        self.current, self.solved = current, solved
        self._hover = False
        self.bind("<Button-1>", lambda _e: self.on_pick(self.info))
        self.bind("<Enter>", lambda _e: self._set_hover(True))
        self.bind("<Leave>", lambda _e: self._set_hover(False))
        self._draw()

    def _set_hover(self, on: bool) -> None:
        self._hover = on
        self._draw()

    def _pill(self, x: float, y: float, text: str, fill: str, fg: str) -> float:
        font = ui_font(8, True)
        pw, ph = text_width(text, font) + 16, 18
        rounded_rect(self, x, y - ph / 2, x + pw, y + ph / 2, ph / 2, fill=fill, outline="")
        self.create_text(x + pw / 2, y, text=text, fill=fg, font=font)
        return x + pw

    def _draw(self) -> None:
        self.delete("all")
        w, h = self.W, self.H
        broken = bool(self.info.get("error"))
        hot = self._hover and not broken

        fill = SURFACE_HI if hot else SURFACE
        edge = ACCENT if self.current else (DIM if hot else BORDER)
        rounded_rect(self, 5, 5, w - 5, h - 5, 14, fill=fill, outline=edge,
                     width=2 if (self.current or hot) else 1)

        self.create_text(20, 26, text=self.info.get("title", ""), anchor="w",
                         fill=DIM if broken else TEXT, font=ui_font(12, True))
        if self.solved:
            self.create_oval(w - 26, 21, w - 16, 31, fill=INNOCENT, outline="")
            self.create_text(w - 32, 26, text="Solved", anchor="e", fill=INNOCENT, font=ui_font(8, True))
        elif self.current:
            self.create_text(w - 20, 26, text="Playing", anchor="e", fill=ACCENT, font=ui_font(8, True))

        size = self.info.get("size")
        if broken or not size:
            self.create_text(w / 2, 78, text="Invalid file", fill=CRIMINAL, font=ui_font(10, True))
            return

        gap = 3
        s = max(8, min(20, int(68 / size) - gap))
        total = size * s + (size - 1) * gap
        x0, y0 = (w - total) / 2, 78 - total / 2
        starter = self.info.get("starter")
        for r in range(size):
            for c in range(size):
                cid = f"{chr(ord('A') + c)}{r + 1}"
                x, y = x0 + c * (s + gap), y0 + r * (s + gap)
                lit = cid == starter
                rounded_rect(self, x, y, x + s, y + s, 3, fill=ACCENT if lit else SURFACE_HI,
                             outline="" if lit else BORDER)

        right = self._pill(18, h - 24, f"{size}\u00d7{size}", BORDER, "white")
        difficulty = str(self.info.get("difficulty") or "").lower()
        if difficulty:
            self._pill(right + 6, h - 24, difficulty.capitalize(),
                       DIFFICULTY_COLOR.get(difficulty, MUTED), INK)


class LevelSelectDialog(tk.Toplevel):
    COLUMNS = 5

    def __init__(self, master, levels: List[Dict[str, Any]], on_select: Callable[[Dict[str, Any]], None],
                 current: Optional[str] = None, solved: Iterable[str] = (), folder: str = "",
                 empty_message: str = "No levels found."):
        super().__init__(master)
        self.title("Select level")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.transient(master)
        self._levels = levels
        self._on_select = on_select
        solved = set(solved)

        head = tk.Frame(self, bg=BG)
        head.pack(fill="x", padx=28, pady=(24, 4))
        tk.Label(head, text="Select a level", bg=BG, fg=TEXT, font=ui_font(18, True)).pack(anchor="w")
        tk.Label(head, text=folder or f"{len(levels)} levels", bg=BG, fg=MUTED,
                 font=ui_font(9)).pack(anchor="w", pady=(4, 0))

        body = tk.Frame(self, bg=BG)
        body.pack(padx=22, pady=(12, 4))
        if not levels:
            tk.Label(body, text=empty_message, bg=BG, fg=MUTED, font=ui_font(11),
                     justify="center").pack(padx=60, pady=50)
        for i, info in enumerate(levels):
            card = LevelCard(body, info, self._pick, current=(info.get("path") == current),
                             solved=(info.get("path") in solved))
            card.grid(row=i // self.COLUMNS, column=i % self.COLUMNS, padx=6, pady=6)

        footer = tk.Frame(self, bg=BG)
        footer.pack(fill="x", padx=28, pady=(6, 22))
        self.note = tk.Label(footer, text="Click a level, or press 1-9 and 0. Esc to close.",
                             bg=BG, fg=MUTED, font=ui_font(9), anchor="w", justify="left")
        self.note.pack(side="left")
        RoundedButton(footer, "Close", self.destroy, width=90, height=34, surface=BG).pack(side="right")

        self.update_idletasks()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        x = master.winfo_rootx() + (master.winfo_width() - w) // 2
        y = master.winfo_rooty() + (master.winfo_height() - h) // 2
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.bind("<Escape>", lambda _e: self.destroy())
        self.bind("<Key>", self._on_key)
        try:
            self.wait_visibility()
            self.grab_set()
        except tk.TclError:
            pass
        self.focus_set()

    def _pick(self, info: Dict[str, Any]) -> None:
        if info.get("error"):                      
            name = str(info.get("path", "")).replace("\\", "/").rsplit("/", 1)[-1]
            self.note.configure(text=f"{name}: {info['error']}", fg=CRIMINAL)
            return
        self.destroy()                             
        self._on_select(info)

    def _on_key(self, event) -> None:
        key = str(event.keysym)
        digit = key[-1] if key[-1:].isdigit() and (key.isdigit() or key.startswith("KP_")) else None
        if digit is None:
            return
        index = 9 if digit == "0" else int(digit) - 1     
        if index < len(self._levels):
            self._pick(self._levels[index])