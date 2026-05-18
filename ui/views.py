from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import discord

from database import models
from ui.embeds import (
    test_question_embed,
    test_result_embed,
    study_answer_embed,
    grading_embed,
)

if TYPE_CHECKING:
    from database.connection import Database


class ABCDEButtonsView(discord.ui.View):
    """Buttons for answering an ABCDE question during a test."""

    def __init__(
        self,
        options: list[str],
        question: dict[str, object],
        test_session: "TestSession",
    ) -> None:
        super().__init__(timeout=None)
        self.value: str | None = None
        for opt in options:
            letter = opt.split(":")[0].strip().upper()
            btn = discord.ui.Button(
                label=opt,
                style=discord.ButtonStyle.secondary,
                custom_id=f"abcde_{letter}_{question['id']}",
            )
            btn.callback = self._make_callback(letter, test_session)
            self.add_item(btn)

    def _make_callback(self, letter: str, test_session: "TestSession"):
        async def callback(interaction: discord.Interaction) -> None:
            self.value = letter
            self.stop()
            await test_session.handle_abcde_answer(interaction, letter)
        return callback


class DescriptiveAnswerView(discord.ui.View):
    """Button to open modal for descriptive answer during a test."""

    def __init__(self, question: dict[str, object], test_session: "TestSession") -> None:
        super().__init__(timeout=None)
        self.question = question
        self.test_session = test_session

    @discord.ui.button(label="\U0001f4dd Napisz odpowiedź", style=discord.ButtonStyle.primary)
    async def write_answer(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        modal = DescriptiveAnswerModal(self.question, self.test_session)
        await interaction.response.send_modal(modal)


class DescriptiveAnswerModal(discord.ui.Modal):
    def __init__(self, question: dict[str, object], test_session: "TestSession") -> None:
        super().__init__(title="Odpowiedź opisowa")
        self.question = question
        self.test_session = test_session
        self.answer_input = discord.ui.TextInput(
            label="Twoja odpowiedź",
            style=discord.TextStyle.paragraph,
            placeholder="Opisz swoją odpowiedź...",
            max_length=2000,
            required=True,
        )
        self.add_item(self.answer_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self.test_session.handle_descriptive_answer(interaction, self.answer_input.value)


class TestSession:
    """Manages an active test for a user."""

    def __init__(
        self,
        db: Database,
        test_instance_id: int,
        questions: list[dict[str, object]],
        time_limit_minutes: int,
        passing_threshold: int,
        on_finish: object | None = None,
    ) -> None:
        self.db = db
        self.test_instance_id = test_instance_id
        self.questions = questions
        self.current_index = 0
        self.time_limit = time_limit_minutes
        self.passing_threshold = passing_threshold
        self.start_time = datetime.now()
        self.deadline = self.start_time + timedelta(minutes=time_limit_minutes)
        self._finished = False
        self.on_finish = on_finish

    @property
    def time_remaining(self) -> str:
        remaining = self.deadline - datetime.now()
        if remaining.total_seconds() <= 0:
            return "00:00"
        minutes = int(remaining.total_seconds() // 60)
        seconds = int(remaining.total_seconds() % 60)
        return f"{minutes:02d}:{seconds:02d}"

    @property
    def is_expired(self) -> bool:
        return datetime.now() >= self.deadline

    async def show_current_question(self, interaction: discord.Interaction) -> None:
        if self._finished:
            return
        if self.is_expired:
            await self._finish_test(interaction)
            return
        if self.current_index >= len(self.questions):
            await self._finish_test(interaction)
            return

        question = self.questions[self.current_index]
        embed = test_question_embed(
            question,
            self.current_index + 1,
            len(self.questions),
            self.time_remaining,
        )

        if question["type"] == "abcde":
            options = question.get("options", [])
            if isinstance(options, list):
                view = ABCDEButtonsView(options, question, self)
                await interaction.edit_original_response(embed=embed, view=view)
            else:
                await interaction.edit_original_response(embed=embed, view=None)
        else:
            view = DescriptiveAnswerView(question, self)
            await interaction.edit_original_response(embed=embed, view=view)

    async def handle_abcde_answer(self, interaction: discord.Interaction, letter: str) -> None:
        if self._finished:
            return
        question = self.questions[self.current_index]
        is_correct = 1 if letter == question.get("correct_answer") else 0
        points = int(question.get("max_points", 1)) if is_correct else 0

        await models.create_test_answer(
            self.db,
            self.test_instance_id,
            int(question["id"]),
            answer=letter,
            is_correct=is_correct,
            points_awarded=points,
        )

        self.current_index += 1
        await interaction.response.defer()
        await self.show_current_question(interaction)

    async def handle_descriptive_answer(self, interaction: discord.Interaction, answer_text: str) -> None:
        if self._finished:
            return
        question = self.questions[self.current_index]

        await models.create_test_answer(
            self.db,
            self.test_instance_id,
            int(question["id"]),
            answer=answer_text,
            is_correct=None,
            points_awarded=None,
        )

        self.current_index += 1
        await interaction.response.defer()
        await self.show_current_question(interaction)

    async def _finish_test(self, interaction: discord.Interaction) -> None:
        if self._finished:
            return
        self._finished = True

        answers = await models.get_test_answers(self.db, self.test_instance_id)
        abcde_score = sum(
            int(a["points_awarded"] or 0) for a in answers if a["question_type"] == "abcde"
        )
        abcde_total = sum(
            int(a["max_points"] or 1) for a in answers if a["question_type"] == "abcde"
        )
        has_descriptive = any(a["question_type"] == "descriptive" for a in answers)
        descriptive_total = sum(
            int(a["max_points"] or 0) for a in answers if a["question_type"] == "descriptive"
        )

        status = "grading" if has_descriptive else "graded"
        update_kwargs: dict[str, object] = {
            "status": status,
            "completed_at": datetime.now().isoformat(),
            "abcde_score": abcde_score,
            "abcde_total": abcde_total,
            "descriptive_total": descriptive_total,
        }
        if not has_descriptive:
            total = abcde_total
            total_pct = round(abcde_score / total * 100, 1) if total > 0 else 0
            passed = 1 if total_pct >= self.passing_threshold else 0
            update_kwargs.update({
                "total_percent": total_pct,
                "passed": passed,
                "graded_at": datetime.now().isoformat(),
            })

        await models.update_test_instance(self.db, self.test_instance_id, **update_kwargs)

        if self.on_finish and callable(self.on_finish):
            self.on_finish()

        embed = test_result_embed(
            self.test_instance_id,
            abcde_score,
            abcde_total,
            0 if not has_descriptive else None,
            descriptive_total,
            update_kwargs.get("total_percent") if not has_descriptive else None,
            bool(update_kwargs.get("passed")) if not has_descriptive else None,
            has_ungraded=has_descriptive,
        )
        await interaction.edit_original_response(embed=embed, view=None)


class TestStartView(discord.ui.View):
    """Start/Cancel buttons for beginning a test."""

    def __init__(self, test_session: TestSession) -> None:
        super().__init__(timeout=120)
        self.test_session = test_session
        self.started = False

    @discord.ui.button(label="Rozpocznij test", style=discord.ButtonStyle.green, emoji="\u25b6\ufe0f")
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.started = True
        self.stop()
        await interaction.response.defer()
        await self.test_session.show_current_question(interaction)

    @discord.ui.button(label="Anuluj", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.stop()
        await models.update_test_instance(
            self.test_session.db, self.test_session.test_instance_id, status="cancelled"
        )
        await interaction.response.edit_message(
            content="\u274c Test anulowany.", embed=None, view=None
        )


# --------------- Study Views ---------------

class StudyABCDEView(discord.ui.View):
    """Buttons for answering during study mode."""

    def __init__(self, options: list[str], question: dict[str, object]) -> None:
        super().__init__(timeout=300)
        self.value: str | None = None
        self.question = question
        for opt in options:
            letter = opt.split(":")[0].strip().upper()
            btn = discord.ui.Button(
                label=opt,
                style=discord.ButtonStyle.secondary,
                custom_id=f"study_{letter}_{question['id']}",
            )
            btn.callback = self._make_callback(letter)
            self.add_item(btn)

    def _make_callback(self, letter: str):
        async def callback(interaction: discord.Interaction) -> None:
            self.value = letter
            self.stop()
            await interaction.response.defer()
        return callback


class StudyContinueView(discord.ui.View):
    """Continue or End buttons after a study answer."""

    def __init__(self) -> None:
        super().__init__(timeout=300)
        self.action: str | None = None

    @discord.ui.button(label="Następne pytanie", style=discord.ButtonStyle.primary, emoji="\u27a1\ufe0f")
    async def next_question(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.action = "next"
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="Zakończ", style=discord.ButtonStyle.secondary, emoji="\u23f9\ufe0f")
    async def end_session(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.action = "end"
        self.stop()
        await interaction.response.defer()


class FlashcardRevealView(discord.ui.View):
    """Reveal button for flashcard mode."""

    def __init__(self) -> None:
        super().__init__(timeout=300)
        self.revealed = False

    @discord.ui.button(label="Odkryj odpowiedź", style=discord.ButtonStyle.primary, emoji="\U0001f50d")
    async def reveal(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.revealed = True
        self.stop()
        await interaction.response.defer()


class FlashcardRatingView(discord.ui.View):
    """Self-rating after seeing flashcard answer."""

    def __init__(self) -> None:
        super().__init__(timeout=300)
        self.rating: str | None = None
        self.action: str | None = None

    @discord.ui.button(label="Tak \u2705", style=discord.ButtonStyle.green)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.rating = "yes"
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="Nie \u274c", style=discord.ButtonStyle.red)
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.rating = "no"
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="Częściowo \U0001f914", style=discord.ButtonStyle.secondary)
    async def partial(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.rating = "partial"
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="Następna fiszka \u27a1\ufe0f", style=discord.ButtonStyle.primary, row=1)
    async def next_card(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.action = "next"
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="Zakończ \u23f9\ufe0f", style=discord.ButtonStyle.secondary, row=1)
    async def end_cards(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.action = "end"
        self.stop()
        await interaction.response.defer()


# --------------- Grading Views ---------------

class GradingPointsView(discord.ui.View):
    """Point selection buttons for grading descriptive answers."""

    def __init__(self, max_points: int) -> None:
        super().__init__(timeout=300)
        self.points: int | None = None
        self.custom = False

        presets = [0]
        if max_points >= 6:
            presets.extend([max_points // 3, max_points // 2, max_points * 7 // 10])
        elif max_points >= 3:
            presets.extend([max_points // 2])
        presets.append(max_points)

        for p in presets:
            btn = discord.ui.Button(
                label=f"{p} pkt",
                style=discord.ButtonStyle.secondary,
            )
            btn.callback = self._make_callback(p)
            self.add_item(btn)

        custom_btn = discord.ui.Button(
            label="Inna wartość",
            style=discord.ButtonStyle.primary,
        )
        custom_btn.callback = self._custom_callback
        self.add_item(custom_btn)

    def _make_callback(self, points: int):
        async def callback(interaction: discord.Interaction) -> None:
            self.points = points
            self.stop()
            await interaction.response.defer()
        return callback

    async def _custom_callback(self, interaction: discord.Interaction) -> None:
        self.custom = True
        self.stop()
        modal = CustomPointsModal()
        await interaction.response.send_modal(modal)


class CustomPointsModal(discord.ui.Modal):
    def __init__(self) -> None:
        super().__init__(title="Punkty")
        self.points_input = discord.ui.TextInput(
            label="Ile punktów?",
            placeholder="Wpisz liczbę...",
            max_length=5,
            required=True,
        )
        self.add_item(self.points_input)
        self.value: int | None = None

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            self.value = int(self.points_input.value)
        except ValueError:
            await interaction.response.send_message("Nieprawidłowa liczba.", ephemeral=True)
            return
        await interaction.response.defer()


class GradingCommentModal(discord.ui.Modal):
    def __init__(self, points: int) -> None:
        super().__init__(title=f"Komentarz do oceny ({points} pkt)")
        self.comment_input = discord.ui.TextInput(
            label="Komentarz (opcjonalny)",
            style=discord.TextStyle.paragraph,
            placeholder="Wpisz komentarz...",
            required=False,
            max_length=1000,
        )
        self.add_item(self.comment_input)
        self.comment: str | None = None

    async def on_submit(self, interaction: discord.Interaction) -> None:
        self.comment = self.comment_input.value or None
        await interaction.response.defer()
