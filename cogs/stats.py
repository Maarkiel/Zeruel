from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from database import models
from ui.embeds import user_stats_embed, ranking_embed
from utils.helpers import is_opiekun, is_moderator

if TYPE_CHECKING:
    from bot import LearningBot


class StatsCog(commands.Cog):
    statystyki = app_commands.Group(name="statystyki", description="Statystyki i postępy")

    def __init__(self, bot: LearningBot) -> None:
        self.bot = bot

    @statystyki.command(name="moje", description="Moje statystyki nauki/testów")
    async def my_stats(self, interaction: discord.Interaction) -> None:
        if not await is_moderator(interaction, self.bot.database):
            await interaction.response.send_message(
                "\u274c Brak uprawnień.", ephemeral=True
            )
            return

        stats = await models.get_user_stats(
            self.bot.database, str(interaction.user.id)
        )
        embed = user_stats_embed(interaction.user, stats)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @statystyki.command(name="moderator", description="Statystyki konkretnego moderatora (Opiekun)")
    @app_commands.describe(user="Moderator")
    async def moderator_stats(
        self, interaction: discord.Interaction, user: discord.Member
    ) -> None:
        if not await is_opiekun(interaction, self.bot.database):
            await interaction.response.send_message(
                "\u274c Brak uprawnień (wymagana rola Opiekuna).", ephemeral=True
            )
            return

        stats = await models.get_user_stats(self.bot.database, str(user.id))
        embed = user_stats_embed(user, stats)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @statystyki.command(name="ranking", description="Ranking moderatorów")
    async def ranking(self, interaction: discord.Interaction) -> None:
        if not await is_moderator(interaction, self.bot.database):
            await interaction.response.send_message(
                "\u274c Brak uprawnień.", ephemeral=True
            )
            return

        guild_id = str(interaction.guild.id) if interaction.guild else None
        ranking_data = await models.get_ranking(self.bot.database, guild_id)
        embed = ranking_embed(ranking_data, interaction.guild)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @statystyki.command(name="pytania", description="Statystyki jakości pytań (Opiekun)")
    @app_commands.describe(kategoria="Kategoria (puste = wszystkie)")
    async def question_stats(
        self, interaction: discord.Interaction, kategoria: str | None = None
    ) -> None:
        if not await is_opiekun(interaction, self.bot.database):
            await interaction.response.send_message(
                "\u274c Brak uprawnień.", ephemeral=True
            )
            return

        category_id = None
        if kategoria:
            cat = await models.get_category_by_name(self.bot.database, kategoria)
            if cat:
                category_id = int(cat["id"])

        stats = await models.get_question_stats(self.bot.database, category_id)
        if not stats:
            await interaction.response.send_message(
                "Brak danych statystycznych.", ephemeral=True
            )
            return

        embed = discord.Embed(
            title="\U0001f4ca Statystyki pytań",
            color=discord.Color.blue(),
        )

        lines: list[str] = []
        for s in stats[:20]:
            q_type = "ABCDE" if s["type"] == "abcde" else "Opisowe"
            pct = f"{s['correctness_pct']}%" if s.get("correctness_pct") is not None else "—"
            times = s.get("times_used", 0)
            content_preview = str(s["content"])[:40]
            lines.append(
                f"**#{s['id']}** [{q_type}] {content_preview}...\n"
                f"   Użyte: {times}x | Poprawność: {pct}"
            )

        embed.description = "\n".join(lines) if lines else "Brak danych."
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @statystyki.command(name="test", description="Szczegóły konkretnego testu (Opiekun)")
    @app_commands.describe(id="ID testu")
    async def test_stats(self, interaction: discord.Interaction, id: int) -> None:
        if not await is_opiekun(interaction, self.bot.database):
            await interaction.response.send_message(
                "\u274c Brak uprawnień.", ephemeral=True
            )
            return

        instance = await models.get_test_instance(self.bot.database, id)
        if not instance:
            await interaction.response.send_message(
                f"\u274c Nie znaleziono testu #{id}.", ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"\U0001f4ca Szczegóły testu #{id}",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Moderator", value=f"<@{instance['user_id']}>", inline=True)
        embed.add_field(name="Status", value=str(instance["status"]), inline=True)
        if instance.get("total_percent") is not None:
            embed.add_field(name="Wynik", value=f"{instance['total_percent']}%", inline=True)
        embed.add_field(
            name="ABCDE",
            value=f"{instance.get('abcde_score', 0)}/{instance.get('abcde_total', 0)}",
            inline=True,
        )
        embed.add_field(
            name="Opisowe",
            value=f"{instance.get('descriptive_score', 0)}/{instance.get('descriptive_total', 0)}",
            inline=True,
        )
        if instance.get("passed") is not None:
            passed_str = "\u2705 Zaliczony" if instance["passed"] else "\u274c Niezaliczony"
            embed.add_field(name="Zaliczenie", value=passed_str, inline=True)

        answers = await models.get_test_answers(self.bot.database, id)
        if answers:
            details: list[str] = []
            for a in answers:
                q_type = "ABCDE" if a["question_type"] == "abcde" else "Opisowe"
                if a["is_correct"] == 1:
                    icon = "\u2705"
                elif a["is_correct"] == 0:
                    icon = "\u274c"
                else:
                    icon = "\u23f3"
                pts = f"{a.get('points_awarded', '?')}/{a.get('max_points', '?')}"
                details.append(f"{icon} [{q_type}] {pts}")
            embed.add_field(
                name="Odpowiedzi",
                value="\n".join(details[:15]),
                inline=False,
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: LearningBot) -> None:
    await bot.add_cog(StatsCog(bot))
