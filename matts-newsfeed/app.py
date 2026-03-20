"""
app.py — Chris's Cannabis Counter
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

from database import init_db, get_articles, toggle_saved, mark_read, get_article_count, delete_old_articles
from feeds import seed_sources, fetch_all_threaded
from logo import get_ctk_logo, make_cannabis_logo

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

WINDOW_TITLE = "Chris's Cannabis Counter"
WINDOW_SIZE  = "1200x800"
PAGE_SIZE    = 50   # articles shown per page — keeps widget count manageable
BATCH_SIZE   = 15   # cards created per event-loop tick during rendering
BATCH_DELAY  = 20   # ms between render batches (lets the event loop breathe)


# ── Article card ──────────────────────────────────────────────────────────────

class ArticleCard(ctk.CTkFrame):
    """One article row."""

    def __init__(self, master, article: dict, on_save_toggle, **kwargs):
        super().__init__(master, corner_radius=8, **kwargs)
        self.article       = article
        self.on_save_toggle = on_save_toggle
        self.configure(fg_color=("#e8e8e8", "#2b2b2b"))

        text_frame = ctk.CTkFrame(self, fg_color="transparent")
        text_frame.pack(side="left", fill="both", expand=True, padx=10, pady=8)

        ctk.CTkButton(
            text_frame,
            text=article["title"][:120],
            anchor="w",
            fg_color="transparent",
            text_color=("#1a73e8", "#8ab4f8"),
            hover_color=("#d0d0d0", "#3a3a3a"),
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._open,
        ).pack(fill="x")

        source    = article.get("source", "")
        published = article.get("published", "")[:25]
        ctk.CTkLabel(
            text_frame,
            text=f"{source}  |  {published}" if published else source,
            anchor="w", font=ctk.CTkFont(size=11), text_color="gray",
        ).pack(fill="x", pady=(2, 0))

        summary = article.get("summary", "")
        if summary:
            ctk.CTkLabel(
                text_frame,
                text=summary[:220] + ("..." if len(summary) > 220 else ""),
                anchor="w", wraplength=750, justify="left",
                font=ctk.CTkFont(size=12),
            ).pack(fill="x", pady=(4, 0))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent", width=90)
        btn_frame.pack(side="right", padx=8, pady=8)
        btn_frame.pack_propagate(False)

        self.save_btn = ctk.CTkButton(
            btn_frame,
            text="Unsave" if article.get("is_saved") else "Save",
            width=70, height=28, font=ctk.CTkFont(size=11),
            command=self._toggle_save,
        )
        self.save_btn.pack(pady=(0, 4))

        ctk.CTkButton(
            btn_frame, text="Open", width=70, height=28,
            font=ctk.CTkFont(size=11), fg_color="#2d8f2d",
            command=self._open,
        ).pack()

    def _open(self):
        url = self.article.get("url", "")
        if url:
            webbrowser.open(url)
            mark_read(self.article["id"])

    def _toggle_save(self):
        new_state = toggle_saved(self.article["id"])
        self.save_btn.configure(text="Unsave" if new_state else "Save")
        if self.on_save_toggle:
            self.on_save_toggle()


# ── Main app ──────────────────────────────────────────────────────────────────

class App(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title(WINDOW_TITLE)
        self.geometry(WINDOW_SIZE)
        self.minsize(900, 550)

        # ── Per-tab state ─────────────────────────────────────────────────
        self._state = {
            "nj":       {"page": 0, "articles": []},
            "national": {"page": 0, "articles": []},
        }

        self._saved_only    = False
        self._search_query  = ""
        self._render_tokens = {}   # cancel stale render chains on re-render

        self._build_ui()

        # DB init + source seed (fast — runs synchronously, no network)
        init_db()
        seed_sources()

        # Load whatever is already in the DB, then kick off a live fetch
        self._refresh_articles()
        self._update_stats()
        self._start_fetch()

    # ── UI construction ───────────────────────────────────────────────────

    def _build_ui(self):
        # Window icon
        try:
            from PIL import ImageTk
            _ico = make_cannabis_logo(32)
            self._icon_ref = ImageTk.PhotoImage(_ico)
            self.iconphoto(True, self._icon_ref)
        except Exception:
            pass

        # Top bar
        top = ctk.CTkFrame(self, height=70)
        top.pack(fill="x", padx=10, pady=(10, 0))
        top.pack_propagate(False)

        try:
            logo_img = get_ctk_logo(size=54)
            ctk.CTkLabel(top, image=logo_img, text="").pack(side="left", padx=(10, 6))
        except Exception:
            pass

        ctk.CTkLabel(top, text=WINDOW_TITLE,
                     font=ctk.CTkFont(size=20, weight="bold")).pack(side="left", padx=(0, 10))

        self.stats_label = ctk.CTkLabel(top, text="", font=ctk.CTkFont(size=12))
        self.stats_label.pack(side="left", padx=20)

        self.progress_label = ctk.CTkLabel(top, text="",
                                           font=ctk.CTkFont(size=11), text_color="gray")
        self.progress_label.pack(side="right", padx=10)

        self.fetch_btn = ctk.CTkButton(top, text="Refresh Feeds", width=130,
                                       command=self._start_fetch)
        self.fetch_btn.pack(side="right", padx=5)

        # Filter bar
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

        self.saved_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(filt, text="Saved only", variable=self.saved_var,
                        command=self._on_saved_toggle).pack(side="left", padx=15)

        ctk.CTkButton(filt, text="Purge Old (30d)", width=110,
                      fg_color="#8b0000", hover_color="#a52a2a",
                      command=self._purge_old).pack(side="right", padx=5)

        # Tabs
        self.tabview = ctk.CTkTabview(self, anchor="nw")
        self.tabview.pack(fill="both", expand=True, padx=10, pady=(8, 10))

        self._build_tab("🌿  NJ Cannabis",  "nj")
        self._build_tab("🇺🇸  National",     "national")

    def _build_tab(self, label: str, key: str):
        self.tabview.add(label)
        tab = self.tabview.tab(label)

        count_lbl = ctk.CTkLabel(tab, text="", font=ctk.CTkFont(size=11), text_color="gray")
        count_lbl.pack(anchor="e", padx=10, pady=(4, 0))

        scroll = ctk.CTkScrollableFrame(tab)
        scroll.pack(fill="both", expand=True)

        # Fixed pagination bar below the scroll frame
        nav = ctk.CTkFrame(tab, height=38)
        nav.pack(fill="x", padx=4, pady=(2, 4))
        nav.pack_propagate(False)

        self._state[key]["count_lbl"] = count_lbl
        self._state[key]["scroll"]    = scroll
        self._state[key]["nav"]       = nav

    # ── Article loading ───────────────────────────────────────────────────

    def _refresh_articles(self):
        """
        Fire a background thread to query the DB (never block the main thread),
        then hand results back via self.after().
        """
        for key in self._state:
            self._state[key]["count_lbl"].configure(text="Loading…")

        def _query():
            base = dict(
                saved_only=self._saved_only,
                search=self._search_query or None,
                limit=2000,
            )
            nj  = get_articles(category="nj",       **base)
            nat = get_articles(category="national",  **base)
            self.after(0, lambda: self._on_articles_ready(nj, nat))

        threading.Thread(target=_query, daemon=True).start()

    def _on_articles_ready(self, nj: list, nat: list):
        """Called on the main thread once the DB query finishes."""
        self._state["nj"]["articles"]       = nj
        self._state["national"]["articles"] = nat
        self._state["nj"]["page"]           = 0
        self._state["national"]["page"]     = 0

        self._show_page("nj")
        self._show_page("national")
        self._update_stats()

    # ── Pagination ────────────────────────────────────────────────────────

    def _show_page(self, key: str):
        """
        Render the current page for `key` tab.
        1. Rebuild the pagination nav (fast — only a few buttons).
        2. Clear the scroll frame.
        3. Kick off batched card rendering via after().
        """
        st       = self._state[key]
        articles = st["articles"]
        page     = st["page"]
        scroll   = st["scroll"]
        nav      = st["nav"]

        total        = len(articles)
        total_pages  = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        start        = page * PAGE_SIZE
        page_slice   = articles[start : start + PAGE_SIZE]

        # Update count label
        st["count_lbl"].configure(
            text=f"{total} articles  •  page {page + 1} of {total_pages}"
        )

        # Rebuild pagination nav
        for w in nav.winfo_children():
            w.destroy()

        if total_pages > 1:
            ctk.CTkButton(
                nav, text="← Prev", width=85, height=28,
                state="normal" if page > 0 else "disabled",
                command=lambda k=key, p=page - 1: self._go_page(k, p),
            ).pack(side="left", padx=6, pady=4)

            ctk.CTkLabel(
                nav,
                text=f"Page {page + 1} of {total_pages}",
                font=ctk.CTkFont(size=11),
            ).pack(side="left", padx=8)

            ctk.CTkButton(
                nav, text="Next →", width=85, height=28,
                state="normal" if page < total_pages - 1 else "disabled",
                command=lambda k=key, p=page + 1: self._go_page(k, p),
            ).pack(side="left", padx=6, pady=4)

        # Clear the scroll frame, then batch-render the new page
        self._clear_scroll(scroll)

        if not page_slice:
            ctk.CTkLabel(
                scroll,
                text="No articles found. Click 'Refresh Feeds' to fetch new articles.",
                font=ctk.CTkFont(size=14), text_color="gray",
            ).pack(pady=40)
            return

        # Issue a unique token for this render chain so a stale chain
        # (from a previous _show_page call) stops itself if superseded.
        token = object()
        self._render_tokens[key] = token
        self.after(0, lambda: self._render_batch(scroll, page_slice, 0, key, token))

    def _go_page(self, key: str, page: int):
        self._state[key]["page"] = page
        self._show_page(key)

    # ── Widget management ─────────────────────────────────────────────────

    def _clear_scroll(self, scroll: ctk.CTkScrollableFrame):
        """
        Destroy children in small groups via after() so the event loop
        isn't blocked on a large widget teardown.
        """
        children = scroll.winfo_children()
        if not children:
            return
        # Destroy up to 20 at a time
        for w in children[:20]:
            try:
                w.destroy()
            except Exception:
                pass
        if len(children) > 20:
            self.after(1, lambda: self._clear_scroll(scroll))

    def _render_batch(self, scroll: ctk.CTkScrollableFrame,
                      articles: list, start: int, key: str, token: object):
        """
        Create BATCH_SIZE cards, yield to the event loop, then schedule
        the next batch.  Stops immediately if `token` has been superseded
        (i.e. _show_page was called again for this tab).
        """
        if self._render_tokens.get(key) is not token:
            return   # stale chain — a newer render has taken over

        end = min(start + BATCH_SIZE, len(articles))
        for art in articles[start:end]:
            card = ArticleCard(scroll, art, on_save_toggle=self._update_stats)
            card.pack(fill="x", pady=3)

        if end < len(articles):
            self.after(BATCH_DELAY,
                       lambda: self._render_batch(scroll, articles, end, key, token))

    # ── Stats ─────────────────────────────────────────────────────────────

    def _update_stats(self):
        def _query():
            counts = get_article_count()
            self.after(0, lambda: self.stats_label.configure(
                text=f"Total: {counts['total']}  |  Saved: {counts['saved']}  |  Unread: {counts['unread']}"
            ))
        threading.Thread(target=_query, daemon=True).start()

    # ── Feed fetch ────────────────────────────────────────────────────────

    def _start_fetch(self):
        self.fetch_btn.configure(state="disabled", text="Fetching…")
        self.progress_label.configure(text="Starting…")

        def on_progress(current, total, name):
            self.after(0, lambda: self.progress_label.configure(
                text=f"[{current}/{total}] {name[:50]}"
            ))

        def on_done(new_count):
            def _finish():
                self.fetch_btn.configure(state="normal", text="Refresh Feeds")
                self.progress_label.configure(text=f"Done — {new_count} new articles")
                self._refresh_articles()
            self.after(0, _finish)

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
        def _do():
            delete_old_articles(days=30)
            self.after(0, self._refresh_articles)
        threading.Thread(target=_do, daemon=True).start()


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
