from __future__ import annotations

import random
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from database import models
from ui.embeds import test_question_embed, study_answer_embed
from ui.views import StudyABCDEView, StudyContinueView, FlashcardRevealView, FlashcardRatingView
from utils.helpers import is_moderator

if TYPE_CHECKING:
    from bot import LearningBot


class StudyCog(commands.Cog):
    nauka = app_commands.Group(name="nauka", description="Tryb nauki / douczanie")

    def __init__(self, bot: LearningBot) -> None:
        self.bot = bot

    @nauka.command(name="start", description="Rozpocznij sesję nauki")
    @app_commands.describe(
        kategoria="Kategoria pytań (puste = mix)",
        trudnosc="Trudność 1-3 (puste = mix)",
    )
    async def start_study(
        self,
        interaction: discord.Interaction,
        kategoria: str | None = None,
        trudnosc: int | None = None,
    ) -> None:
        if not await is_moderator(interaction, self.bot.database):
            await interaction.response.send_message(
                "\u274c Brak uprawnień (wymagana rola Moderatora).", ephemeral=True
            )
            return

        category_id = None
        if kategoria:
            cat = await models.get_category_by_name(self.bot.database, kategoria)
            if cat:
                category_id = int(cat["id"])
            else:
                await interaction.response.send_message(
                    f"\u274c Nie znaleziono kategorii: {kategoria}", ephemeral=True
                )
                return

        session_id = await models.create_study_session(
            self.bot.database, str(interaction.user.id), category_id
        )

        await interaction.response.send_message(
            "\U0001f9e0 **Sesja nauki rozpoczęta!**\n"
            "Odpowiadaj na pytania — po każdym dostaniesz feedback.\n"
            "Priorytet mają pytania, w których wcześniej się pomyliłeś.",
            ephemeral=True,
        )

        streak = 0
        questions_practiced = 0
        correct_answers = 0

        while True:
            review = await models.get_review_questions(
                self.bot.database, str(interaction.user.id), category_id
            )
            if review:
                question = random.choice(review)
            else:
                questions_list = await models.get_random_questions(
                    self.bot.database, "abcde", 1,
                    category_id=category_id, difficulty=trudnosc,
                )
                if not questions_list:
                    await interaction.followup.send(
                        "\u274c Brak pytań ABCDE w bazie.", ephemeral=True
                    )
                    break
                question = questions_list[0]

            embed = test_question_embed(
                question, questions_practiced + 1, 0, None
            )
            embed.title = f"\U0001f9e0 Nauka — Pytanie {questions_practiced + 1}"
            embed.color = discord.Color.teal()

            options = question.get("options", [])
            if not isinstance(options, list) or not options:
                continue

            view = StudyABCDEView(options, question)
            msg = await interaction.followup.send(
                embed=embed, view=view, ephemeral=True, wait=True
            )
            timed_out = await view.wait()
            if timed_out or view.value is None:
                break

            correct = view.value == question.get("correct_answer")
            if correct:
                streak += 1
                correct_answers += 1
            else:
                streak = 0

            questions_practiced += 1
            await models.update_study_progress(
                self.bot.database, str(interaction.user.id),
                int(question["id"]), correct,
            )

            answer_embed = study_answer_embed(question, view.value, correct, streak)
            continue_view = StudyContinueView()
            try:
                await msg.edit(embed=answer_embed, view=continue_view)
            except discord.NotFound:
                break

            timed_out = await continue_view.wait()
            if timed_out or continue_view.action == "end":
                break

        await models.update_study_session(
            self.bot.database, session_id,
            questions_practiced=questions_practiced,
            correct_answers=correct_answers,
            ended_at="CURRENT_TIMESTAMP",
        )

        pct = round(correct_answers / questions_practiced * 100, 1) if questions_practiced > 0 else 0
        summary = discord.Embed(
            title="\U0001f4ca Podsumowanie sesji nauki",
            color=discord.Color.teal(),
        )
        summary.add_field(name="Pytań", value=str(questions_practiced), inline=True)
        summary.add_field(name="Poprawnych", value=f"{correct_answers} ({pct}%)", inline=True)
        summary.add_field(name="Najdłuższa seria", value=str(streak), inline=True)
        await interaction.followup.send(embed=summary, ephemeral=True)

    @nauka.command(name="fiszki", description="Tryb fiszek — pytania + odpowiedzi")
    @app_commands.describe(kategoria="Kategoria (puste = mix)")
    async def flashcards(
        self, interaction: discord.Interaction, kategoria: str | None = None
    ) -> None:
        if not await is_moderator(interaction, self.bot.database):
            await interaction.response.send_message(
                "\u274c Brak uprawnień.", ephemeral=True
            )
            return

        category_id = None
        if kategoria:
            cat = await models.get_category_by_name(self.bot.database, kategoria)
            if cat:
                category_id = int(cat["id"])

        questions = await models.get_questions(
            self.bot.database, category_id=category_id
        )
        if not questions:
            await interaction.response.send_message(
                "\u274c Brak pytań w bazie.", ephemeral=True
            )
            return

        random.shuffle(questions)
        await interaction.response.send_message(
            f"\U0001f4da **Tryb fiszek** — {len(questions)} pytań\n"
            "Zobaczysz pytanie, kliknij aby odkryć odpowiedź.",
            ephemeral=True,
        )

        cards_seen = 0
        for question in questions:
            embed = discord.Embed(
                title=f"\U0001f4da Fiszka {cards_seen + 1}/{len(questions)}",
                description=str(question["content"]),
                color=discord.Color.purple(),
            )
            q_type = "ABCDE" if question["type"] == "abcde" else "Opisowe"
            embed.set_footer(text=f"Typ: {q_type}")

            reveal_view = FlashcardRevealView()
            msg = await interaction.followup.send(
                embed=embed, view=reveal_view, ephemeral=True, wait=True
            )
            timed_out = await reveal_view.wait()
            if timed_out or not reveal_view.revealed:
                break

            answer_embed = discord.Embed(
                title=f"\U0001f4da Fiszka {cards_seen + 1}/{len(questions)} — Odpowiedź",
                description=str(question["content"]),
                color=discord.Color.green(),
            )
            if question["type"] == "abcde":
                answer_embed.add_field(
                    name="\u2705 Poprawna odpowiedź",
                    value=str(question.get("correct_answer", "—")),
                    inline=False,
                )
                if question.get("options") and isinstance(question["options"], list):
                    answer_embed.add_field(
                        name="Opcje",
                        value="\n".join(question["options"]),
                        inline=False,
                    )
            else:
                answer_embed.add_field(
                    name="\U0001f4cc Wzorcowa odpowiedź",
                    value=str(question.get("model_answer", "—")),
                    inline=False,
                )
            if question.get("explanation"):
                answer_embed.add_field(
                    name="\U0001f4a1 Wyjaśnienie",
                    value=str(question["explanation"]),
                    inline=False,
                )

            rating_view = FlashcardRatingView()
            answer_embed.add_field(
                name="Czy wiedziałeś/aś odpowiedź?",
                value="Oceń siebie:",
                inline=False,
            )
            try:
                await msg.edit(embed=answer_embed, view=rating_view)
            except discord.NotFound:
                break

            timed_out = await rating_view.wait()
            if timed_out or rating_view.action == "end":
                break

            if rating_view.rating:
                correct = rating_view.rating == "yes"
                await models.update_study_progress(
                    self.bot.database, str(interaction.user.id),
                    int(question["id"]), correct,
                )

            cards_seen += 1

        await interaction.followup.send(
            f"\U0001f4da Sesja fiszek zakończona — przejrzano **{cards_seen}** fiszek.",
            ephemeral=True,
        )

    @nauka.command(name="bledy", description="Powtórka z błędów")
    async def review_errors(self, interaction: discord.Interaction) -> None:
        if not await is_moderator(interaction, self.bot.database):
            await interaction.response.send_message(
                "\u274c Brak uprawnień.", ephemeral=True
            )
            return

        review = await models.get_review_questions(
            self.bot.database, str(interaction.user.id)
        )
        if not review:
            await interaction.response.send_message(
                "\u2705 Nie masz pytań do powtórki — brawo!", ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"\U0001f504 **Powtórka z błędów** — {len(review)} pytań do przejrzenia.",
            ephemeral=True,
        )

        streak = 0
        correct_count = 0
        for i, question in enumerate(review):
            options = question.get("options", [])
            if not isinstance(options, list) or not options:
                continue

            embed = test_question_embed(question, i + 1, len(review), None)
            embed.title = f"\U0001f504 Powtórka — Pytanie {i + 1}/{len(review)}"
            embed.color = discord.Color.orange()

            view = StudyABCDEView(options, question)
            msg = await interaction.followup.send(
                embed=embed, view=view, ephemeral=True, wait=True
            )
            timed_out = await view.wait()
            if timed_out or view.value is None:
                break

            correct = view.value == question.get("correct_answer")
            if correct:
                streak += 1
                correct_count += 1
            else:
                streak = 0

            await models.update_study_progress(
                self.bot.database, str(interaction.user.id),
                int(question["id"]), correct,
            )

            answer_embed = study_answer_embed(question, view.value, correct, streak)
            continue_view = StudyContinueView()
            try:
                await msg.edit(embed=answer_embed, view=continue_view)
            except discord.NotFound:
                break

            timed_out = await continue_view.wait()
            if timed_out or continue_view.action == "end":
                break

        pct = round(correct_count / len(review) * 100, 1) if review else 0
        await interaction.followup.send(
            f"\U0001f504 Powtórka zakończona: **{correct_count}/{len(review)}** ({pct}%) poprawnych.",
            ephemeral=True,
        )


async def setup(bot: LearningBot) -> None:
    await bot.add_cog(StudyCog(bot))
