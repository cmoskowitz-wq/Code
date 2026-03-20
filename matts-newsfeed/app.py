"""
app.py — Matt's Newsfeed
Desktop GUI for browsing cannabis/marijuana/weed news.
Two sections:
  - NJ Cannabis   : New Jersey state-level news
  - National      : Federal / US-wide news
Articles are sorted by date, latest first.
"""

import customtkinter as ctk
import webbrowser
import threading
from datetime import datetime

from database import init_db, get_articles, toggle_saved, mark_read, get_article_count, get_sources, delete_old_articles
from feeds import seed_sources, fetch_all_threaded

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

WINDOW_TITLE = "Matt's Cannabis Newsfeed"
WINDOW_SIZE = "1200x800"


class ArticleCard(ctk.CTkFrame):
    """A single article row in the feed."""

    def __init__(self, master, article: dict, on_save_toggle, **kwargs):
        super().__init__(master, corner_radius=8, **kwargs)
        self.article = article
        self.on_save_toggle = on_save_toggle

        self.configure(fg_color=("#e8e8e8", "#2b2b2b"))

        # Left: text content
        text_frame = ctk.CTkFrame(self, fg_color="transparent")
        text_frame.pack(side="left", fill="both", expand=True, padx=10, pady=8)

        # Title (clickable)
        title = article["title"][:120]
        self.title_btn = ctk.CTkButton(
            text_frame, text=title, anchor="w",
            fg_color="transparent", text_color=("#1a73e8", "#8ab4f8"),
            hover_color=("#d0d0d0", "#3a3a3a"),
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._open_article,
        )
        self.title_btn.pack(fill="x")

        # Meta line
        source = article.get("source", "")
        published = article.get("published", "")[:25]
        meta_text = f"{source}  |  {published}" if published else source
        meta = ctk.CTkLabel(text_frame, text=meta_text, anchor="w",
                            font=ctk.CTkFont(size=11), text_color="gray")
        meta.pack(fill="x", pady=(2, 0))

        # Summary
        summary = article.get("summary", "")
        if summary:
            summary_label = ctk.CTkLabel(
                text_frame, text=summary[:220] + ("..." if len(summary) > 220 else ""),
                anchor="w", wraplength=750, justify="left",
                font=ctk.CTkFont(size=12),
            )
            summary_label.pack(fill="x", pady=(4, 0))

        # Right: action buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent", width=90)
        btn_frame.pack(side="right", padx=8, pady=8)
        btn_frame.pack_propagate(False)

        save_text = "Unsave" if article.get("is_saved") else "Save"
        self.save_btn = ctk.CTkButton(
            btn_frame, text=save_text, width=70, height=28,
            font=ctk.CTkFont(size=11), command=self._toggle_save,
        )
        self.save_btn.pack(pady=(0, 4))

        open_btn = ctk.CTkButton(
            btn_frame, text="Open", width=70, height=28,
            font=ctk.CTkFont(size=11), fg_color="#2d8f2d",
            command=self._open_article,
        )
        open_btn.pack()

    def _open_article(self):
        url = self.article.get("url", "")
        if url:
            webbrowser.open(url)
            mark_read(self.article["id"])

    def _toggle_save(self):
        new_state = toggle_saved(self.article["id"])
        self.save_btn.configure(text="Unsave" if new_state else "Save")
        if self.on_save_toggle:
            self.on_save_toggle()


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(WINDOW_TITLE)
        self.geometry(WINDOW_SIZE)
        self.minsize(900, 550)

        # State
        self._saved_only = False
        self._search_query = ""

        self._build_ui()

        # Init DB and seed cannabis sources
        init_db()
        seed_sources()

        # Initial load
        self._refresh_articles()
        self._update_stats()

        # Auto-fetch on startup
        self._start_fetch()

    def _build_ui(self):
        # ── Top bar ──────────────────────────────────────────────────────
        top = ctk.CTkFrame(self, height=50)
        top.pack(fill="x", padx=10, pady=(10, 0))
        top.pack_propagate(False)

        ctk.CTkLabel(top, text=WINDOW_TITLE,
                     font=ctk.CTkFont(size=18, weight="bold")).pack(side="left", padx=10)

        self.stats_label = ctk.CTkLabel(top, text="", font=ctk.CTkFont(size=12))
        self.stats_label.pack(side="left", padx=20)

        self.fetch_btn = ctk.CTkButton(top, text="Refresh Feeds", width=130,
                                       command=self._start_fetch)
        self.fetch_btn.pack(side="right", padx=5)

        self.progress_label = ctk.CTkLabel(top, text="", font=ctk.CTkFont(size=11),
                                           text_color="gray")
        self.progress_label.pack(side="right", padx=10)

        # ── Filter bar ───────────────────────────────────────────────────
        filt = ctk.CTkFrame(self, height=40)
        filt.pack(fill="x", padx=10, pady=(5, 0))
        filt.pack_propagate(False)

        self.search_entry = ctk.CTkEntry(filt, placeholder_text="Search articles...", width=280)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<Return>", lambda e: self._apply_search())

        ctk.CTkButton(filt, text="Search", width=70,
                      command=self._apply_search).pack(side="left", padx=2)
        ctk.CTkButton(filt, text="Clear", width=60, fg_color="gray",
                      command=self._clear_search).pack(side="left", padx=2)

        # Saved toggle
        self.saved_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(filt, text="Saved only", variable=self.saved_var,
                        command=self._on_saved_toggle).pack(side="left", padx=15)

        # Purge button
        ctk.CTkButton(filt, text="Purge Old (30d)", width=110,
                      fg_color="#8b0000", hover_color="#a52a2a",
                      command=self._purge_old).pack(side="right", padx=5)

        # ── Two-tab feed view ────────────────────────────────────────────
        self.tabview = ctk.CTkTabview(self, anchor="nw")
        self.tabview.pack(fill="both", expand=True, padx=10, pady=(8, 10))

        self.tabview.add("🌿  NJ Cannabis")
        self.tabview.add("🇺🇸  National")

        self.nj_count_label = ctk.CTkLabel(
            self.tabview.tab("🌿  NJ Cannabis"), text="",
            font=ctk.CTkFont(size=11), text_color="gray"
        )
        self.nj_count_label.pack(anchor="e", padx=10, pady=(4, 0))

        self.nj_scroll = ctk.CTkScrollableFrame(self.tabview.tab("🌿  NJ Cannabis"))
        self.nj_scroll.pack(fill="both", expand=True)

        self.nat_count_label = ctk.CTkLabel(
            self.tabview.tab("🇺🇸  National"), text="",
            font=ctk.CTkFont(size=11), text_color="gray"
        )
        self.nat_count_label.pack(anchor="e", padx=10, pady=(4, 0))

        self.nat_scroll = ctk.CTkScrollableFrame(self.tabview.tab("🇺🇸  National"))
        self.nat_scroll.pack(fill="both", expand=True)

    # ── Article rendering ─────────────────────────────────────────────────

    def _refresh_articles(self):
        base = dict(
            saved_only=self._saved_only,
            search=self._search_query or None,
            limit=500,
        )

        nj_articles = get_articles(category="nj", **base)
        nat_articles = get_articles(category="national", **base)

        self._render_tab(self.nj_scroll, nj_articles)
        self._render_tab(self.nat_scroll, nat_articles)

        self.nj_count_label.configure(text=f"{len(nj_articles)} articles")
        self.nat_count_label.configure(text=f"{len(nat_articles)} articles")

    def _render_tab(self, frame: ctk.CTkScrollableFrame, articles: list):
        for w in frame.winfo_children():
            w.destroy()
        if not articles:
            ctk.CTkLabel(
                frame,
                text="No articles found. Click 'Refresh Feeds' to fetch new articles.",
                font=ctk.CTkFont(size=14), text_color="gray",
            ).pack(pady=40)
            return
        for art in articles:
            card = ArticleCard(frame, art, on_save_toggle=self._update_stats)
            card.pack(fill="x", pady=3)

    # ── Stats ─────────────────────────────────────────────────────────────

    def _update_stats(self):
        counts = get_article_count()
        self.stats_label.configure(
            text=f"Total: {counts['total']}  |  Saved: {counts['saved']}  |  Unread: {counts['unread']}"
        )

    # ── Fetch ─────────────────────────────────────────────────────────────

    def _start_fetch(self):
        self.fetch_btn.configure(state="disabled", text="Fetching...")
        self.progress_label.configure(text="Starting...")

        def on_progress(current, total, name):
            self.after(0, lambda: self.progress_label.configure(
                text=f"[{current}/{total}] {name[:50]}"
            ))

        def on_done(new_count):
            def _update():
                self.fetch_btn.configure(state="normal", text="Refresh Feeds")
                self.progress_label.configure(text=f"Done — {new_count} new articles")
                self._refresh_articles()
                self._update_stats()
            self.after(0, _update)

        fetch_all_threaded(progress_callback=on_progress, done_callback=on_done)

    # ── Filter callbacks ──────────────────────────────────────────────────

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
        delete_old_articles(days=30)
        self._refresh_articles()
        self._update_stats()


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
