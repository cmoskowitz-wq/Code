"""
app.py — Matt's Newsfeed
Desktop GUI for browsing kratom and NJ Cannabis news.
Uses CTkTextbox for article rendering — single widget, instant paint, no per-article frames.
"""

import customtkinter as ctk
import webbrowser
import threading
from datetime import datetime

from database import init_db, get_articles, toggle_saved, mark_read, get_article_count, purge_old_articles
from feeds import seed_sources, fetch_all_threaded

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

WINDOW_TITLE = "Matt's Newsfeed"
WINDOW_SIZE = "1100x780"

# ── Colors ────────────────────────────────────────────────────────────────────
TITLE_COLOR  = "#8ab4f8"   # blue link
SAVE_COLOR   = "#f0b429"   # amber save tag
META_COLOR   = "#888888"   # gray meta line
SEP_COLOR    = "#444444"   # separator
READ_COLOR   = "#555555"   # dimmed read title
BG_DARK      = "#1e1e1e"


class ArticleFeed(ctk.CTkFrame):
    """
    A pane that renders articles as formatted text inside a single CTkTextbox.
    Titles are clickable; a [Save] tag per article toggles bookmarks.
    No per-article widget creation — repaint is instant.
    """

    def __init__(self, master, tab: str, nj_filter: bool = False, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._tab = tab
        self._nj_filter = nj_filter
        self._articles: list = []
        self._search_query = ""
        self._saved_only = False
        self._category: str | None = None

        self._build_filter_bar()
        self._build_textbox()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_filter_bar(self):
        bar = ctk.CTkFrame(self, height=38, fg_color=("#2a2a2a", "#2a2a2a"))
        bar.pack(fill="x", pady=(0, 4))
        bar.pack_propagate(False)

        self._search_entry = ctk.CTkEntry(bar, placeholder_text="Search…", width=220)
        self._search_entry.pack(side="left", padx=(6, 2), pady=4)
        self._search_entry.bind("<Return>", lambda _e: self._apply_search())

        ctk.CTkButton(bar, text="Search", width=64, height=28,
                      command=self._apply_search).pack(side="left", padx=2, pady=4)
        ctk.CTkButton(bar, text="Clear", width=52, height=28,
                      fg_color="gray40", hover_color="gray50",
                      command=self._clear_search).pack(side="left", padx=2, pady=4)

        self._cat_var = ctk.StringVar(value="All")
        categories = ["All", "news", "advocacy", "science", "regulation", "community", "business", "general"]
        ctk.CTkOptionMenu(bar, variable=self._cat_var, values=categories,
                          command=self._on_category_change, width=130,
                          height=28).pack(side="left", padx=8, pady=4)

        self._saved_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(bar, text="Saved only", variable=self._saved_var,
                        command=self._on_saved_toggle,
                        height=28).pack(side="left", padx=6, pady=4)

    def _build_textbox(self):
        self._textbox = ctk.CTkTextbox(
            self,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            wrap="word",
            activate_scrollbars=True,
            fg_color=BG_DARK,
        )
        self._textbox.pack(fill="both", expand=True)
        # Grab the underlying tk.Text widget for tag/binding access
        self._tw = self._textbox._textbox
        self._tw.configure(cursor="arrow", spacing1=2, spacing3=2)

        # Static tag styles (configured once)
        self._tw.tag_configure("title",   foreground=TITLE_COLOR, font=("Segoe UI", 13, "bold"))
        self._tw.tag_configure("title_read", foreground=READ_COLOR, font=("Segoe UI", 13, "bold"))
        self._tw.tag_configure("save",    foreground=SAVE_COLOR,  font=("Segoe UI", 11))
        self._tw.tag_configure("meta",    foreground=META_COLOR,  font=("Segoe UI", 10))
        self._tw.tag_configure("summary", foreground="#cccccc",   font=("Segoe UI", 11))
        self._tw.tag_configure("sep",     foreground=SEP_COLOR,   font=("Segoe UI", 8))

        # Hover cursor on clickable tags
        for tag in ("title", "title_read", "save"):
            self._tw.tag_bind(tag, "<Enter>", lambda _e: self._tw.configure(cursor="hand2"))
            self._tw.tag_bind(tag, "<Leave>", lambda _e: self._tw.configure(cursor="arrow"))

    # ── Rendering ─────────────────────────────────────────────────────────────

    def render_articles(self, articles: list):
        self._articles = articles
        tw = self._tw

        tw.configure(state="normal")
        tw.delete("1.0", "end")

        # Remove stale per-article tags
        for tag in tw.tag_names():
            if tag.startswith(("open_", "save_")):
                tw.tag_delete(tag)

        if not articles:
            tw.insert("end", "\n  No articles found. Click 'Refresh Feeds' to fetch new articles.\n", "meta")
            tw.configure(state="disabled")
            return

        for i, art in enumerate(articles):
            title = art["title"][:120]
            is_read = art.get("is_read", 0)
            is_saved = art.get("is_saved", 0)
            title_tag_style = "title_read" if is_read else "title"

            open_tag = f"open_{i}"
            save_tag = f"save_{i}"

            # Title (clickable)
            tw.insert("end", title, (title_tag_style, open_tag))

            # [Save] / [Saved] inline
            save_label = "  [Saved ✓]" if is_saved else "  [Save]"
            tw.insert("end", save_label + "\n", (save_tag, "save"))

            # Meta line
            source   = art.get("source", "")
            cat      = art.get("category", "")
            pub_raw  = art.get("published_parsed") or art.get("published", "")
            pub_disp = pub_raw[:10] if pub_raw else "no date"
            tw.insert("end", f"  {source}  ·  {cat}  ·  {pub_disp}\n", "meta")

            # Summary
            summary = (art.get("summary") or "").strip()
            if summary:
                tw.insert("end", f"  {summary[:220]}{'…' if len(summary) > 220 else ''}\n", "summary")

            tw.insert("end", "  ─────────────────────────────────────────────────────\n", "sep")

            # Per-article click bindings (capture loop vars via default args)
            tw.tag_bind(open_tag, "<Button-1>",
                        lambda _e, url=art["url"], aid=art["id"], idx=i:
                        self._open_article(url, aid, idx))
            tw.tag_bind(save_tag, "<Button-1>",
                        lambda _e, aid=art["id"], idx=i:
                        self._toggle_save(aid, idx))
            for t in (open_tag, save_tag):
                tw.tag_bind(t, "<Enter>", lambda _e: tw.configure(cursor="hand2"))
                tw.tag_bind(t, "<Leave>", lambda _e: tw.configure(cursor="arrow"))

        tw.configure(state="disabled")

    # ── Article actions ───────────────────────────────────────────────────────

    def _open_article(self, url: str, article_id: int, idx: int):
        if url:
            webbrowser.open(url)
            mark_read(article_id)
            # Visually dim the title without re-rendering the full list
            open_tag = f"open_{idx}"
            self._tw.tag_remove("title", open_tag + ".first", open_tag + ".last")
            self._tw.tag_add("title_read", open_tag + ".first", open_tag + ".last")
            if idx < len(self._articles):
                self._articles[idx]["is_read"] = 1

    def _toggle_save(self, article_id: int, idx: int):
        new_state = toggle_saved(article_id)
        save_tag = f"save_{idx}"
        if idx < len(self._articles):
            self._articles[idx]["is_saved"] = 1 if new_state else 0
        # Update just the save label text in-place
        tw = self._tw
        tw.configure(state="normal")
        start = f"{save_tag}.first"
        end   = f"{save_tag}.last"
        try:
            tw.delete(start, end)
            label = "  [Saved ✓]" if new_state else "  [Save]"
            tw.insert(start, label, (save_tag, "save"))
        except Exception:
            pass
        tw.configure(state="disabled")

    # ── Filtering callbacks ───────────────────────────────────────────────────

    def refresh(self):
        cat = self._cat_var.get()
        articles = get_articles(
            saved_only=self._saved_only,
            category=None if cat == "All" else cat,
            search=self._search_query or None,
            tab=self._tab,
            nj_filter=self._nj_filter,
            limit=300,
        )
        self.render_articles(articles)

    def _apply_search(self):
        self._search_query = self._search_entry.get().strip()
        self.refresh()

    def _clear_search(self):
        self._search_entry.delete(0, "end")
        self._search_query = ""
        self.refresh()

    def _on_category_change(self, _value):
        self.refresh()

    def _on_saved_toggle(self):
        self._saved_only = self._saved_var.get()
        self.refresh()


# ── Main App ──────────────────────────────────────────────────────────────────

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(WINDOW_TITLE)
        self.geometry(WINDOW_SIZE)
        self.minsize(800, 520)

        self._build_ui()

        # DB init → purge old → seed sources
        init_db()
        purge_old_articles(days=90)
        seed_sources()

        # Initial display
        self._refresh_all_tabs()
        self._update_stats()

        # Kick off background fetch
        self._start_fetch()

    def _build_ui(self):
        # ── Top bar ───────────────────────────────────────────────────────────
        top = ctk.CTkFrame(self, height=50)
        top.pack(fill="x", padx=10, pady=(10, 0))
        top.pack_propagate(False)

        ctk.CTkLabel(top, text=WINDOW_TITLE,
                     font=ctk.CTkFont(size=18, weight="bold")).pack(side="left", padx=10)

        self._stats_label = ctk.CTkLabel(top, text="", font=ctk.CTkFont(size=12))
        self._stats_label.pack(side="left", padx=20)

        self._fetch_btn = ctk.CTkButton(top, text="Refresh Feeds", width=120,
                                        command=self._start_fetch)
        self._fetch_btn.pack(side="right", padx=5)

        self._progress_label = ctk.CTkLabel(top, text="", font=ctk.CTkFont(size=11),
                                             text_color="gray")
        self._progress_label.pack(side="right", padx=10)

        # ── Tab view ──────────────────────────────────────────────────────────
        tabs = ctk.CTkTabview(self, anchor="nw")
        tabs.pack(fill="both", expand=True, padx=10, pady=8)

        tabs.add("🌿 Kratom")
        tabs.add("🍃 NJ Cannabis")

        self._kratom_feed = ArticleFeed(tabs.tab("🌿 Kratom"), tab="kratom", nj_filter=False)
        self._kratom_feed.pack(fill="both", expand=True)

        self._nj_feed = ArticleFeed(tabs.tab("🍃 NJ Cannabis"), tab="nj_cannabis", nj_filter=True)
        self._nj_feed.pack(fill="both", expand=True)

    def _refresh_all_tabs(self):
        self._kratom_feed.refresh()
        self._nj_feed.refresh()

    def _update_stats(self):
        counts = get_article_count()
        self._stats_label.configure(
            text=f"Total: {counts['total']}  |  Saved: {counts['saved']}  |  Unread: {counts['unread']}"
        )

    def _start_fetch(self):
        self._fetch_btn.configure(state="disabled", text="Fetching…")
        self._progress_label.configure(text="Starting…")

        def on_progress(current, total, name):
            self.after(0, lambda: self._progress_label.configure(
                text=f"[{current}/{total}] {name[:45]}"))

        def on_done(new_count):
            def _update():
                self._fetch_btn.configure(state="normal", text="Refresh Feeds")
                self._progress_label.configure(text=f"Done — {new_count} new articles")
                self._refresh_all_tabs()
                self._update_stats()
            self.after(0, _update)

        fetch_all_threaded(progress_callback=on_progress, done_callback=on_done)


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
