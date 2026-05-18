from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from database import models
from ui.embeds import grading_embed, test_result_embed
from ui.views import GradingPointsView, GradingCommentModal
from utils.helpers import is_opiekun

if TYPE_CHECKING:
    from bot import LearningBot


class GradingCog(commands.Cog):
    ocena = app_commands.Group(name="ocena", description="Ocenianie odpowiedzi opisowych")

    def __init__(self, bot: LearningBot) -> None:
        self.bot = bot

    @ocena.command(name="lista", description="Lista odpowiedzi oczekujących na ocenę")
    async def grading_list(self, interaction: discord.Interaction) -> None:
        if not await is_opiekun(interaction, self.bot.database):
            await interaction.response.send_message(
                "\u274c Brak uprawnień (wymagana rola Opiekuna).", ephemeral=True
            )
            return

        guild_id = str(interaction.guild.id) if interaction.guild else None
        ungraded = await models.get_ungraded_answers(self.bot.database, guild_id)

        if not ungraded:
            await interaction.response.send_message(
                "\u2705 Brak odpowiedzi do oceny.", ephemeral=True
            )
            return

        lines: list[str] = []
        for a in ungraded[:20]:
            content_preview = str(a["question_content"])[:50]
            lines.append(
                f"\u23f3 **#{a['id']}** — <@{a['user_id']}> | "
                f"Test #{a['test_id']} | {content_preview}..."
            )

        embed = discord.Embed(
            title=f"\U0001f4dd Do oceny ({len(ungraded)})",
            description="\n".join(lines),
            color=discord.Color.orange(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @ocena.command(name="ocen", description="Oceń konkretną odpowiedź")
    @app_commands.describe(id_odpowiedzi="ID odpowiedzi do oceny")
    async def grade_single(self, interaction: discord.Interaction, id_odpowiedzi: int) -> None:
        if not await is_opiekun(interaction, self.bot.database):
            await interaction.response.send_message(
                "\u274c Brak uprawnień.", ephemeral=True
            )
            return

        guild_id = str(interaction.guild.id) if interaction.guild else None
        ungraded = await models.get_ungraded_answers(self.bot.database, guild_id)
        answer = next((a for a in ungraded if int(a["id"]) == id_odpowiedzi), None)

        if not answer:
            await interaction.response.send_message(
                f"\u274c Nie znaleziono odpowiedzi #{id_odpowiedzi} do oceny.",
                ephemeral=True,
            )
            return

        await self._grade_answer(interaction, answer)

    @ocena.command(name="szybka", description="Szybkie ocenianie kolejki odpowiedzi")
    async def quick_grade(self, interaction: discord.Interaction) -> None:
        if not await is_opiekun(interaction, self.bot.database):
            await interaction.response.send_message(
                "\u274c Brak uprawnień.", ephemeral=True
            )
            return

        guild_id = str(interaction.guild.id) if interaction.guild else None
        ungraded = await models.get_ungraded_answers(self.bot.database, guild_id)

        if not ungraded:
            await interaction.response.send_message(
                "\u2705 Brak odpowiedzi do oceny.", ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"\U0001f4dd Rozpoczynam szybkie ocenianie ({len(ungraded)} odpowiedzi)...",
            ephemeral=True,
        )

        graded_count = 0
        for answer in ungraded:
            result = await self._grade_answer_quick(interaction, answer)
            if result:
                graded_count += 1
            else:
                break

        await interaction.followup.send(
            f"\u2705 Oceniono **{graded_count}** odpowiedzi.", ephemeral=True
        )

    async def _grade_answer(
        self, interaction: discord.Interaction, answer: dict[str, object]
    ) -> None:
        embed = grading_embed(answer)
        max_points = int(answer.get("max_points", 10))
        points_view = GradingPointsView(max_points)

        await interaction.response.send_message(
            embed=embed, view=points_view, ephemeral=True
        )
        await points_view.wait()

        if points_view.points is None and not points_view.custom:
            return

        points = points_view.points or 0

        comment_modal = GradingCommentModal(points)

        class CommentTrigger(discord.ui.View):
            def __init__(self) -> None:
                super().__init__(timeout=60)

            @discord.ui.button(label="Dodaj komentarz (opcjonalnie)", style=discord.ButtonStyle.secondary)
            async def add_comment(
                self_btn, btn_interaction: discord.Interaction, button: discord.ui.Button
            ) -> None:
                await btn_interaction.response.send_modal(comment_modal)

            @discord.ui.button(label="Zapisz bez komentarza", style=discord.ButtonStyle.primary)
            async def save_no_comment(
                self_btn, btn_interaction: discord.Interaction, button: discord.ui.Button
            ) -> None:
                self_btn.view.stop()  # type: ignore[union-attr]
                await btn_interaction.response.defer()

        comment_view = CommentTrigger()
        await interaction.edit_original_response(
            content=f"Przyznano **{points}/{max_points}** pkt.",
            embed=embed,
            view=comment_view,
        )
        await comment_view.wait()

        comment = comment_modal.comment
        await models.grade_answer(
            self.bot.database,
            int(answer["id"]),
            points,
            str(interaction.user.id),
            comment,
        )

        test_instance_id = int(answer["test_instance_id"])
        await self._check_and_finalize_test(interaction, test_instance_id)

        await interaction.edit_original_response(
            content=f"\u2705 Odpowiedź **#{answer['id']}** oceniona: {points}/{max_points} pkt.",
            embed=None,
            view=None,
        )

    async def _grade_answer_quick(
        self, interaction: discord.Interaction, answer: dict[str, object]
    ) -> bool:
        embed = grading_embed(answer)
        max_points = int(answer.get("max_points", 10))
        points_view = GradingPointsView(max_points)

        msg = await interaction.followup.send(
            embed=embed, view=points_view, ephemeral=True, wait=True
        )
        timed_out = await points_view.wait()
        if timed_out or (points_view.points is None and not points_view.custom):
            return False

        points = points_view.points or 0

        await models.grade_answer(
            self.bot.database,
            int(answer["id"]),
            points,
            str(interaction.user.id),
        )

        test_instance_id = int(answer["test_instance_id"])
        await self._check_and_finalize_test(interaction, test_instance_id)

        try:
            await msg.edit(
                content=f"\u2705 #{answer['id']}: {points}/{max_points} pkt",
                embed=None,
                view=None,
            )
        except discord.NotFound:
            pass

        return True

    async def _check_and_finalize_test(
        self, interaction: discord.Interaction, test_instance_id: int
    ) -> None:
        fully_graded = await models.check_test_fully_graded(self.bot.database, test_instance_id)
        if not fully_graded:
            return

        scores = await models.calculate_test_score(self.bot.database, test_instance_id)
        await models.update_test_instance(
            self.bot.database,
            test_instance_id,
            status="graded",
            graded_at=datetime.now().isoformat(),
            graded_by=str(interaction.user.id),
        )

        instance = await models.get_test_instance(self.bot.database, test_instance_id)
        if not instance:
            return

        user_id = int(instance["user_id"])
        try:
            user = await self.bot.fetch_user(user_id)
            embed = test_result_embed(
                test_instance_id,
                int(scores["abcde_score"]),
                int(scores["abcde_total"]),
                int(scores["descriptive_score"]),
                int(scores["descriptive_total"]),
                float(scores["total_percent"]),
                bool(scores["passed"]),
            )

            answers = await models.get_test_answers(self.bot.database, test_instance_id)
            comments: list[str] = []
            for a in answers:
                if a.get("admin_comment"):
                    comments.append(
                        f"\u2022 *{str(a['question_content'])[:40]}...* — {a['admin_comment']}"
                    )
            if comments:
                embed.add_field(
                    name="\U0001f4ac Komentarze opiekuna",
                    value="\n".join(comments[:10]),
                    inline=False,
                )

            await user.send(embed=embed)
        except (discord.Forbidden, discord.NotFound):
            pass

        guild_id = str(instance["guild_id"])
        config = await models.get_guild_config(self.bot.database, guild_id)
        results_channel_id = config.get("test_results_channel_id")
        if results_channel_id:
            channel = self.bot.get_channel(int(results_channel_id))
            if channel and isinstance(channel, discord.TextChannel):
                embed = test_result_embed(
                    test_instance_id,
                    int(scores["abcde_score"]),
                    int(scores["abcde_total"]),
                    int(scores["descriptive_score"]),
                    int(scores["descriptive_total"]),
                    float(scores["total_percent"]),
                    bool(scores["passed"]),
                )
                embed.set_author(name=f"Test <@{user_id}>")
                await channel.send(embed=embed)


async def setup(bot: LearningBot) -> None:
    await bot.add_cog(GradingCog(bot))
