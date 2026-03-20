"""
app.py — Chris's Cannabis Counter
Desktop GUI for browsing cannabis/marijuana/weed news.
  Tab 1 — NJ Cannabis   : New Jersey state-level news
  Tab 2 — National      : Federal / US-wide news

Articles displayed in a CTkTextbox (single native widget, no per-article
frame creation) so rendering is instantaneous regardless of article count.
Articles sorted latest-first; paginated at 50 per page.
"""

import tkinter as tk
import customtkinter as ctk
import webbrowser
import threading

from database import (
    init_db, get_articles, toggle_saved, mark_read,
    get_article_count, delete_old_articles,
)
from feeds import seed_sources, fetch_all_threaded
from logo import get_ctk_logo, make_cannabis_logo

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

WINDOW_TITLE = "Chris's Cannabis Counter"
WINDOW_SIZE  = "1200x820"
PAGE_SIZE    = 50


# ── Colour palette (dark mode) ────────────────────────────────────────────────
_C = {
    "bg":      "#1e1e1e",
    "bg_text": "#1e1e1e",
    "title":   "#8ab4f8",
    "title_h": "#b8d0ff",
    "meta":    "#888888",
    "summary": "#c8c8c8",
    "save_off": "#4db84d",
    "save_on":  "#e8a020",
    "divider":  "#2e2e2e",
    "cursor":   "#1e1e1e",
}

_FONT_TITLE   = ("Segoe UI", 13, "bold")
_FONT_META    = ("Segoe UI", 10)
_FONT_SUMMARY = ("Segoe UI", 11)
_FONT_NAV     = ("Segoe UI", 11)


# ── Main app ──────────────────────────────────────────────────────────────────

class App(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title(WINDOW_TITLE)
        self.geometry(WINDOW_SIZE)
        self.minsize(900, 580)

        self._saved_only   = False
        self._search_query = ""

        # Per-tab state: articles list + current page index
        self._state = {
            "nj":       {"articles": [], "page": 0},
            "national": {"articles": [], "page": 0},
        }

        self._build_ui()

        init_db()
        seed_sources()           # fast — no network
        self._refresh_articles() # kicks off background DB thread
        self._start_fetch()      # kicks off background network fetch

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        # Window icon
        try:
            from PIL import ImageTk
            self._icon_ref = ImageTk.PhotoImage(make_cannabis_logo(32))
            self.iconphoto(True, self._icon_ref)
        except Exception:
            pass

        # ── Top bar ───────────────────────────────────────────────────────
        top = ctk.CTkFrame(self, height=70)
        top.pack(fill="x", padx=10, pady=(10, 0))
        top.pack_propagate(False)

        try:
            _logo = get_ctk_logo(size=54)
            ctk.CTkLabel(top, image=_logo, text="").pack(side="left", padx=(10, 6))
        except Exception:
            pass

        ctk.CTkLabel(top, text=WINDOW_TITLE,
                     font=ctk.CTkFont(size=20, weight="bold")).pack(side="left")

        self.stats_lbl = ctk.CTkLabel(top, text="", font=ctk.CTkFont(size=12))
        self.stats_lbl.pack(side="left", padx=20)

        self.progress_lbl = ctk.CTkLabel(top, text="",
                                         font=ctk.CTkFont(size=11), text_color="gray")
        self.progress_lbl.pack(side="right", padx=10)

        self.fetch_btn = ctk.CTkButton(top, text="Refresh Feeds", width=130,
                                       command=self._start_fetch)
        self.fetch_btn.pack(side="right", padx=5)

        # ── Filter bar ────────────────────────────────────────────────────
        filt = ctk.CTkFrame(self, height=42)
        filt.pack(fill="x", padx=10, pady=(6, 0))
        filt.pack_propagate(False)

        self.search_entry = ctk.CTkEntry(filt, placeholder_text="Search articles…", width=280)
        self.search_entry.pack(side="left", padx=(8, 4), pady=6)
        self.search_entry.bind("<Return>", lambda _e: self._apply_search())

        ctk.CTkButton(filt, text="Search", width=72,
                      command=self._apply_search).pack(side="left", padx=2)
        ctk.CTkButton(filt, text="Clear", width=60, fg_color="gray",
                      command=self._clear_search).pack(side="left", padx=2)

        self.saved_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(filt, text="Saved only", variable=self.saved_var,
                        command=self._on_saved_toggle).pack(side="left", padx=14)

        ctk.CTkButton(filt, text="Purge >90 days", width=120,
                      fg_color="#8b0000", hover_color="#a52a2a",
                      command=self._purge_old).pack(side="right", padx=8)

        # ── Tabs ──────────────────────────────────────────────────────────
        self.tabview = ctk.CTkTabview(self, anchor="nw")
        self.tabview.pack(fill="both", expand=True, padx=10, pady=(8, 10))

        self._build_tab("🌿  NJ Cannabis", "nj")
        self._build_tab("🇺🇸  National",    "national")

    def _build_tab(self, label: str, key: str):
        self.tabview.add(label)
        tab = self.tabview.tab(label)

        # Count / status line
        count_lbl = ctk.CTkLabel(tab, text="", font=ctk.CTkFont(size=11), text_color="gray")
        count_lbl.pack(anchor="e", padx=12, pady=(4, 2))

        # Article textbox — single native widget, no per-article frame overhead
        textbox = ctk.CTkTextbox(
            tab,
            wrap="word",
            activate_scrollbars=True,
            fg_color=_C["bg_text"],
        )
        textbox.pack(fill="both", expand=True)
        textbox.configure(state="disabled")

        # Preconfigure static tags on the underlying tk.Text
        tb = textbox._textbox
        tb.configure(
            bg=_C["bg_text"],
            fg="#ffffff",
            insertbackground=_C["cursor"],
            selectbackground="#3a3a5c",
            relief="flat",
            borderwidth=0,
            padx=12,
            pady=6,
        )
        tb.tag_configure("title",   foreground=_C["title"],   font=_FONT_TITLE,
                         spacing1=14, spacing3=2)
        tb.tag_configure("meta",    foreground=_C["meta"],    font=_FONT_META,   spacing3=3)
        tb.tag_configure("summary", foreground=_C["summary"], font=_FONT_SUMMARY, spacing3=4)
        tb.tag_configure("save_off", foreground=_C["save_off"], font=_FONT_META)
        tb.tag_configure("save_on",  foreground=_C["save_on"],  font=_FONT_META)
        tb.tag_configure("divider", foreground=_C["divider"], font=("Segoe UI", 4), spacing1=2)

        # Pagination bar — fixed height, outside the textbox
        nav = ctk.CTkFrame(tab, height=40)
        nav.pack(fill="x", padx=4, pady=(4, 4))
        nav.pack_propagate(False)

        self._state[key].update({
            "count_lbl": count_lbl,
            "textbox":   textbox,
            "nav":       nav,
        })

    # ── Article loading (background thread → main thread) ─────────────────────

    def _refresh_articles(self):
        for key in self._state:
            self._state[key]["count_lbl"].configure(text="Loading…")

        def _query():
            base = dict(
                saved_only=self._saved_only,
                search=self._search_query or None,
                days_back=90,
                limit=2000,
            )
            nj  = get_articles(category="nj",       **base)
            nat = get_articles(category="national",  **base)
            self.after(0, lambda: self._on_ready(nj, nat))

        threading.Thread(target=_query, daemon=True).start()

    def _on_ready(self, nj: list, nat: list):
        self._state["nj"]["articles"]       = nj
        self._state["national"]["articles"] = nat
        self._state["nj"]["page"]           = 0
        self._state["national"]["page"]     = 0
        self._show_page("nj")
        self._show_page("national")
        self._update_stats()

    # ── Page rendering (instant — text insertion only) ────────────────────────

    def _show_page(self, key: str):
        st       = self._state[key]
        articles = st["articles"]
        page     = st["page"]
        textbox  = st["textbox"]
        tb       = textbox._textbox
        nav      = st["nav"]

        total       = len(articles)
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        start       = page * PAGE_SIZE
        page_slice  = articles[start : start + PAGE_SIZE]

        st["count_lbl"].configure(
            text=f"{total} articles  •  page {page + 1} of {total_pages}"
        )

        # ── Rebuild pagination nav ────────────────────────────────────────
        for w in nav.winfo_children():
            w.destroy()

        if total_pages > 1:
            ctk.CTkButton(
                nav, text="← Prev", width=90, height=30,
                font=ctk.CTkFont(size=12),
                state="normal" if page > 0 else "disabled",
                command=lambda k=key, p=page - 1: self._go_page(k, p),
            ).pack(side="left", padx=8, pady=5)

            ctk.CTkLabel(
                nav,
                text=f"Page {page + 1} of {total_pages}",
                font=ctk.CTkFont(size=12),
            ).pack(side="left", padx=10)

            ctk.CTkButton(
                nav, text="Next →", width=90, height=30,
                font=ctk.CTkFont(size=12),
                state="normal" if page < total_pages - 1 else "disabled",
                command=lambda k=key, p=page + 1: self._go_page(k, p),
            ).pack(side="left", padx=8, pady=5)

        # ── Render articles into textbox ──────────────────────────────────
        # Remove per-article dynamic tags from a previous render
        for tag in tb.tag_names():
            if tag.startswith("_a_"):
                tb.tag_delete(tag)

        textbox.configure(state="normal")
        tb.delete("1.0", "end")

        if not page_slice:
            tb.insert("end", "\n  No articles found.\n  Click 'Refresh Feeds' to fetch news.",
                      "meta")
            textbox.configure(state="disabled")
            return

        for art in page_slice:
            aid    = art.get("id", id(art))
            t_tag  = f"_a_t{aid}"   # title link tag
            sv_tag = f"_a_s{aid}"   # save toggle tag

            # Title tag — unique per article so each has its own binding
            tb.tag_configure(t_tag, foreground=_C["title"], font=_FONT_TITLE,
                             spacing1=14, spacing3=2)
            tb.tag_bind(t_tag, "<Button-1>",
                        lambda _e, a=art: self._open_art(a))
            tb.tag_bind(t_tag, "<Enter>",
                        lambda _e: tb.configure(cursor="hand2"))
            tb.tag_bind(t_tag, "<Leave>",
                        lambda _e: tb.configure(cursor="xterm"))

            # Save tag
            saved     = bool(art.get("is_saved"))
            sv_colour = _C["save_on"] if saved else _C["save_off"]
            sv_label  = "  ★ Saved  " if saved else "  ☆ Save  "
            tb.tag_configure(sv_tag, foreground=sv_colour, font=_FONT_META)
            tb.tag_bind(sv_tag, "<Button-1>",
                        lambda _e, a=art, k=key: self._toggle_save_art(a, k))
            tb.tag_bind(sv_tag, "<Enter>",
                        lambda _e: tb.configure(cursor="hand2"))
            tb.tag_bind(sv_tag, "<Leave>",
                        lambda _e: tb.configure(cursor="xterm"))

            # Insert content
            tb.insert("end", "  " + art["title"][:140] + "\n", t_tag)

            src = art.get("source", "")[:70]
            pub = (art.get("published") or "")[:16].replace("T", " ").rstrip("Z")
            meta_str = f"  {src}"
            if pub:
                meta_str += f"  •  {pub}"
            tb.insert("end", meta_str, "meta")
            tb.insert("end", sv_label + "\n", sv_tag)

            summary = (art.get("summary") or "").strip()
            if summary:
                tb.insert("end", "  " + summary[:240] + "\n", "summary")

            tb.insert("end", "\n", "divider")

        textbox.configure(state="disabled")
        tb.yview_moveto(0.0)   # always scroll to top on page change

    def _go_page(self, key: str, page: int):
        self._state[key]["page"] = page
        self._show_page(key)

    # ── Article actions ───────────────────────────────────────────────────────

    def _open_art(self, art: dict):
        url = art.get("url", "")
        if url:
            webbrowser.open(url)
            mark_read(art["id"])

    def _toggle_save_art(self, art: dict, key: str):
        toggle_saved(art["id"])
        art["is_saved"] = not art.get("is_saved")
        self._show_page(key)   # re-render current page to reflect star change
        self._update_stats()

    # ── Stats ─────────────────────────────────────────────────────────────────

    def _update_stats(self):
        def _q():
            counts = get_article_count()
            self.after(0, lambda: self.stats_lbl.configure(
                text=f"Total: {counts['total']}  |  Saved: {counts['saved']}  |  Unread: {counts['unread']}"
            ))
        threading.Thread(target=_q, daemon=True).start()

    # ── Feed fetch ────────────────────────────────────────────────────────────

    def _start_fetch(self):
        self.fetch_btn.configure(state="disabled", text="Fetching…")
        self.progress_lbl.configure(text="Starting…")

        def on_progress(current, total, name):
            self.after(0, lambda: self.progress_lbl.configure(
                text=f"[{current}/{total}] {name[:55]}"
            ))

        def on_done(new_count):
            def _finish():
                self.fetch_btn.configure(state="normal", text="Refresh Feeds")
                self.progress_lbl.configure(text=f"Done — {new_count} new articles")
                self._refresh_articles()
            self.after(0, _finish)

        fetch_all_threaded(progress_callback=on_progress, done_callback=on_done)

    # ── Filter callbacks ──────────────────────────────────────────────────────

    def _apply_search(self):
        self._search_query = self.search_entry.get().strip()
        self._refresh_articles()

    def _clear_search(self):
        self.search_entry.delete(0, "end")
        self._search_query = ""
        self._refresh_articles()

    def _on_saved_toggle(self):
        self._saved_only = self.saved_var.get()
        self._refresh_articles()

    def _purge_old(self):
        def _do():
            delete_old_articles(days=90)
            self.after(0, self._refresh_articles)
        threading.Thread(target=_do, daemon=True).start()


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
