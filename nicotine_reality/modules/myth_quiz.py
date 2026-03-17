"""
myth_quiz.py — Myth vs Reality interactive quiz.
8 questions, one at a time, with fade transitions and explanations.
"""

import json
import os
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QFrame, QProgressBar,
                              QGraphicsOpacityEffect, QApplication)
from modules.theme import (BG, SURFACE, CARD, ACCENT, ACCENT2, TEXT, TEXT_DIM,
                            WARNING, SUCCESS, BORDER, font, fade_in)

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "data", "myths.json")


def _load_questions():
    try:
        with open(DATA_PATH, "r") as f:
            return json.load(f)["questions"]
    except Exception:
        return []


# ── Answer button with flash effect ──────────────────────────────────────────

class AnswerButton(QPushButton):
    def __init__(self, text: str):
        super().__init__(text)
        self.setFixedHeight(56)
        self.setFont(font(13, bold=True))
        self._base_style = (
            f"background:{SURFACE}; color:{TEXT}; border:2px solid {BORDER};"
            f" border-radius:6px; font-size:13px; font-weight:bold;"
        )
        self._correct_style = (
            f"background:#003300; color:#00ee44; border:2px solid {SUCCESS};"
            f" border-radius:6px; font-size:13px; font-weight:bold;"
        )
        self._wrong_style = (
            f"background:#330000; color:#ee3322; border:2px solid {ACCENT};"
            f" border-radius:6px; font-size:13px; font-weight:bold;"
        )
        self.setStyleSheet(self._base_style)

    def flash_correct(self):
        self.setStyleSheet(self._correct_style)

    def flash_wrong(self):
        self.setStyleSheet(self._wrong_style)

    def reset(self):
        self.setStyleSheet(self._base_style)
        self.setEnabled(True)


# ── Question card ─────────────────────────────────────────────────────────────

class QuestionCard(QFrame):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(
            f"background:{CARD}; border:1px solid {BORDER}; border-radius:10px;"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(20)

        self.question_lbl = QLabel()
        self.question_lbl.setFont(font(15, bold=True))
        self.question_lbl.setWordWrap(True)
        self.question_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.question_lbl.setMinimumHeight(80)
        layout.addWidget(self.question_lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(16)
        self.myth_btn = AnswerButton("MYTH")
        self.reality_btn = AnswerButton("REALITY")
        btn_row.addWidget(self.myth_btn, 1)
        btn_row.addWidget(self.reality_btn, 1)
        layout.addLayout(btn_row)

        # Explanation panel (hidden until answered)
        self.expl_frame = QFrame()
        self.expl_frame.setStyleSheet(
            f"background:{SURFACE}; border-radius:6px; border:1px solid {BORDER};"
        )
        self.expl_frame.setVisible(False)
        expl_layout = QVBoxLayout(self.expl_frame)
        expl_layout.setContentsMargins(16, 12, 16, 12)

        self.verdict_lbl = QLabel()
        self.verdict_lbl.setFont(font(12, bold=True))
        expl_layout.addWidget(self.verdict_lbl)

        self.expl_lbl = QLabel()
        self.expl_lbl.setFont(font(10))
        self.expl_lbl.setStyleSheet(f"color:{TEXT_DIM};")
        self.expl_lbl.setWordWrap(True)
        expl_layout.addWidget(self.expl_lbl)

        layout.addWidget(self.expl_frame)

    def load_question(self, q: dict):
        self.question_lbl.setText(q["question"])
        self.myth_btn.reset()
        self.reality_btn.reset()
        self.expl_frame.setVisible(False)
        self._correct = q["correct_answer"]
        self._explanation = q["explanation"]

    def show_result(self, chosen: str) -> bool:
        correct = (chosen == self._correct)
        if chosen == "myth":
            if correct:
                self.myth_btn.flash_correct()
            else:
                self.myth_btn.flash_wrong()
                self.reality_btn.flash_correct()
        else:
            if correct:
                self.reality_btn.flash_correct()
            else:
                self.reality_btn.flash_wrong()
                self.myth_btn.flash_correct()

        verdict = "✓ Correct!" if correct else "✗ Incorrect"
        color = SUCCESS if correct else ACCENT
        self.verdict_lbl.setText(verdict)
        self.verdict_lbl.setStyleSheet(f"color:{color}; font-size:12px; font-weight:bold;")
        self.expl_lbl.setText(self._explanation)
        self.expl_frame.setVisible(True)
        self.myth_btn.setEnabled(False)
        self.reality_btn.setEnabled(False)
        fade_in(self.expl_frame, duration=300)
        return correct


# ── Score / results screen ────────────────────────────────────────────────────

class ResultsScreen(QWidget):
    def __init__(self, score: int, total: int, on_restart, on_home):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        pct = score / total * 100
        grade = "Expert" if pct >= 88 else "Informed" if pct >= 62 else "Learning"
        grade_color = SUCCESS if pct >= 75 else WARNING if pct >= 50 else ACCENT

        header = QLabel("Quiz Complete")
        header.setFont(font(22, bold=True))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        score_lbl = QLabel(f"{score} / {total}")
        score_lbl.setFont(font(48, bold=True))
        score_lbl.setStyleSheet(f"color:{grade_color};")
        score_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(score_lbl)

        grade_lbl = QLabel(f"Level: {grade}")
        grade_lbl.setFont(font(16))
        grade_lbl.setStyleSheet(f"color:{grade_color};")
        grade_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(grade_lbl)

        messages = {
            "Expert":   "You clearly know your facts. Now help a friend learn what you know.",
            "Informed": "Good knowledge — a few myths still slipped through. Review the explanations above.",
            "Learning": "Several myths fooled you. That's exactly why this quiz exists — industry tactics work.",
        }
        msg_lbl = QLabel(messages[grade])
        msg_lbl.setFont(font(11))
        msg_lbl.setStyleSheet(f"color:{TEXT_DIM};")
        msg_lbl.setWordWrap(True)
        msg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg_lbl.setMaximumWidth(500)
        layout.addWidget(msg_lbl)

        # Share text (copy to clipboard)
        share_text = (
            f"I scored {score}/{total} on the Nicotine Reality Myth Quiz. "
            f"Test your own knowledge — most people believe at least 3 of these myths."
        )
        share_btn = QPushButton("📋  Copy result to clipboard")
        share_btn.setFixedWidth(300)
        share_btn.clicked.connect(lambda: QApplication.clipboard().setText(share_text))
        layout.addWidget(share_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        again_btn = QPushButton("Try Again")
        again_btn.setFixedWidth(160)
        again_btn.clicked.connect(on_restart)
        btn_row.addWidget(again_btn)

        home_btn = QPushButton("← Main Menu")
        home_btn.setObjectName("secondary")
        home_btn.setFixedWidth(160)
        home_btn.clicked.connect(on_home)
        btn_row.addWidget(home_btn)

        layout.addLayout(btn_row)


# ── Main MythQuiz screen ──────────────────────────────────────────────────────

class MythQuiz(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self._questions = _load_questions()
        self._index = 0
        self._score = 0
        self._answered = False
        self._build_ui()
        self._load_question()
        fade_in(self)

    def _build_ui(self):
        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(24, 16, 24, 16)
        self.root.setSpacing(12)

        # Back + title
        top = QHBoxLayout()
        self.back_btn = QPushButton("← Back")
        self.back_btn.setObjectName("back_btn")
        self.back_btn.setFixedWidth(90)
        self.back_btn.clicked.connect(lambda: self.main_window.go_to_screen("nav"))
        top.addWidget(self.back_btn)
        top.addStretch()
        title = QLabel("Myth or Reality?")
        title.setFont(font(18, bold=True))
        top.addWidget(title)
        top.addStretch()
        self.root.addLayout(top)

        subtitle = QLabel("Test what you really know about nicotine. Pick MYTH or REALITY for each statement.")
        subtitle.setFont(font(11))
        subtitle.setStyleSheet(f"color:{TEXT_DIM};")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.root.addWidget(subtitle)

        # Progress
        prog_row = QHBoxLayout()
        self.prog_bar = QProgressBar()
        self.prog_bar.setRange(0, len(self._questions))
        self.prog_bar.setValue(0)
        self.prog_bar.setFixedHeight(8)
        self.prog_bar.setTextVisible(False)
        prog_row.addWidget(self.prog_bar)
        self.prog_lbl = QLabel("1 / 8")
        self.prog_lbl.setFont(font(10))
        self.prog_lbl.setStyleSheet(f"color:{TEXT_DIM};")
        self.prog_lbl.setFixedWidth(44)
        prog_row.addWidget(self.prog_lbl)
        self.root.addLayout(prog_row)

        # Question card
        self.card = QuestionCard()
        self.card.myth_btn.clicked.connect(lambda: self._answer("myth"))
        self.card.reality_btn.clicked.connect(lambda: self._answer("reality"))
        self.root.addWidget(self.card, 1)

        # Next button (hidden until answered)
        self.next_btn = QPushButton("Next Question →")
        self.next_btn.setVisible(False)
        self.next_btn.clicked.connect(self._next_question)
        self.root.addWidget(self.next_btn, alignment=Qt.AlignmentFlag.AlignRight)

        # Placeholder for results screen
        self._results_widget = None

    def _load_question(self):
        if self._index >= len(self._questions):
            self._show_results()
            return
        q = self._questions[self._index]
        self.card.load_question(q)
        self.prog_bar.setValue(self._index)
        self.prog_lbl.setText(f"{self._index + 1} / {len(self._questions)}")
        self._answered = False
        self.next_btn.setVisible(False)

    def _answer(self, choice: str):
        if self._answered:
            return
        self._answered = True
        correct = self.card.show_result(choice)
        if correct:
            self._score += 1
        self.next_btn.setVisible(True)
        label = "Finish" if self._index == len(self._questions) - 1 else "Next Question →"
        self.next_btn.setText(label)

    def _next_question(self):
        self._index += 1
        # Fade out card, then load next
        effect = QGraphicsOpacityEffect(self.card)
        self.card.setGraphicsEffect(effect)
        out = QPropertyAnimation(effect, b"opacity", self)
        out.setDuration(200)
        out.setStartValue(1.0)
        out.setEndValue(0.0)
        out.setEasingCurve(QEasingCurve.Type.InOutQuad)
        out.finished.connect(self._on_fade_done)
        out.start()
        self._fade_out_anim = out

    def _on_fade_done(self):
        self._load_question()
        fade_in(self.card, duration=300)

    def _show_results(self):
        self.prog_bar.setValue(len(self._questions))
        # Replace card and next btn with results
        self.card.setVisible(False)
        self.next_btn.setVisible(False)
        self.back_btn.setVisible(False)

        results = ResultsScreen(
            self._score, len(self._questions),
            on_restart=self._restart,
            on_home=lambda: self.main_window.go_to_screen("nav"),
        )
        self.root.addWidget(results)
        fade_in(results)
        self._results_widget = results

    def _restart(self):
        self._index = 0
        self._score = 0
        if self._results_widget:
            self._results_widget.deleteLater()
            self._results_widget = None
        self.card.setVisible(True)
        self.back_btn.setVisible(True)
        self._load_question()
        fade_in(self.card)
