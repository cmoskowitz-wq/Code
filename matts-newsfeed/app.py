"""
app.py — Matt's Newsfeed
Desktop GUI for browsing kratom news from multiple sources.
"""

import customtkinter as ctk
import webbrowser
import threading
from datetime import datetime

from database import init_db, get_articles, toggle_saved, mark_read, get_article_count, get_sources, delete_old_articles
from feeds import seed_sources, fetch_all_threaded

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

WINDOW_TITLE = "Matt's Kratom Newsfeed"
WINDOW_SIZE = "1100x750"


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
        category = article.get("category", "general")
        meta_text = f"{source}  |  {category}  |  {published}"
        meta = ctk.CTkLabel(text_frame, text=meta_text, anchor="w",
                            font=ctk.CTkFont(size=11), text_color="gray")
        meta.pack(fill="x", pady=(2, 0))

        # Summary
        summary = article.get("summary", "")
        if summary:
            summary_label = ctk.CTkLabel(
                text_frame, text=summary[:200] + ("..." if len(summary) > 200 else ""),
                anchor="w", wraplength=700, justify="left",
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
        self.minsize(800, 500)

        # State
        self._current_filter_source = None
        self._current_filter_category = None
        self._saved_only = False
        self._search_query = ""

        self._build_ui()

        # Init DB and seed
        init_db()
        seed_sources()

        # Initial load
        self._refresh_articles()
        self._update_stats()

        # Auto-fetch on startup
        self._start_fetch()

    def _build_ui(self):
        # Top bar
        top = ctk.CTkFrame(self, height=50)
        top.pack(fill="x", padx=10, pady=(10, 0))
        top.pack_propagate(False)

        ctk.CTkLabel(top, text=WINDOW_TITLE, font=ctk.CTkFont(size=18, weight="bold")).pack(side="left", padx=10)

        self.stats_label = ctk.CTkLabel(top, text="", font=ctk.CTkFont(size=12))
        self.stats_label.pack(side="left", padx=20)

        self.fetch_btn = ctk.CTkButton(top, text="Refresh Feeds", width=120, command=self._start_fetch)
        self.fetch_btn.pack(side="right", padx=5)

        self.progress_label = ctk.CTkLabel(top, text="", font=ctk.CTkFont(size=11), text_color="gray")
        self.progress_label.pack(side="right", padx=10)

        # Filter bar
        filt = ctk.CTkFrame(self, height=40)
        filt.pack(fill="x", padx=10, pady=(5, 0))
        filt.pack_propagate(False)

        self.search_entry = ctk.CTkEntry(filt, placeholder_text="Search articles...", width=250)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<Return>", lambda e: self._apply_search())

        ctk.CTkButton(filt, text="Search", width=70, command=self._apply_search).pack(side="left", padx=2)
        ctk.CTkButton(filt, text="Clear", width=60, fg_color="gray", command=self._clear_search).pack(side="left", padx=2)

        # Category filter
        self.category_var = ctk.StringVar(value="All Categories")
        categories = ["All Categories", "news", "advocacy", "science", "regulation", "community", "general"]
        cat_menu = ctk.CTkOptionMenu(filt, variable=self.category_var, values=categories, command=self._on_category_change, width=150)
        cat_menu.pack(side="left", padx=10)

        # Saved toggle
        self.saved_var = ctk.BooleanVar(value=False)
        saved_cb = ctk.CTkCheckBox(filt, text="Saved only", variable=self.saved_var, command=self._on_saved_toggle)
        saved_cb.pack(side="left", padx=10)

        # Purge button
        ctk.CTkButton(filt, text="Purge Old", width=90, fg_color="#8b0000", hover_color="#a52a2a",
                       command=self._purge_old).pack(side="right", padx=5)

        # Scrollable article list
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)

    def _refresh_articles(self):
        # Clear current cards
        for w in self.scroll_frame.winfo_children():
            w.destroy()

        cat = self._current_filter_category
        if cat == "All Categories":
            cat = None

        articles = get_articles(
            saved_only=self._saved_only,
            source=self._current_filter_source,
            category=cat,
            search=self._search_query or None,
            limit=300,
        )

        if not articles:
            ctk.CTkLabel(self.scroll_frame, text="No articles found. Click 'Refresh Feeds' to fetch new articles.",
                         font=ctk.CTkFont(size=14), text_color="gray").pack(pady=40)
            return

        for art in articles:
            card = ArticleCard(self.scroll_frame, art, on_save_toggle=self._update_stats)
            card.pack(fill="x", pady=3)

    def _update_stats(self):
        counts = get_article_count()
        self.stats_label.configure(
            text=f"Total: {counts['total']}  |  Saved: {counts['saved']}  |  Unread: {counts['unread']}"
        )

    def _start_fetch(self):
        self.fetch_btn.configure(state="disabled", text="Fetching...")
        self.progress_label.configure(text="Starting...")

        def on_progress(current, total, name):
            self.after(0, lambda: self.progress_label.configure(text=f"[{current}/{total}] {name}"))

        def on_done(new_count):
            def _update():
                self.fetch_btn.configure(state="normal", text="Refresh Feeds")
                self.progress_label.configure(text=f"Done — {new_count} new articles")
                self._refresh_articles()
                self._update_stats()
            self.after(0, _update)

        fetch_all_threaded(progress_callback=on_progress, done_callback=on_done)

    def _apply_search(self):
        self._search_query = self.search_entry.get().strip()
        self._refresh_articles()

    def _clear_search(self):
        self.search_entry.delete(0, "end")
        self._search_query = ""
        self._refresh_articles()

    def _on_category_change(self, value):
        self._current_filter_category = value if value != "All Categories" else None
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
