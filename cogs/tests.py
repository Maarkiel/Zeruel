from __future__ import annotations

import random
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from database import models
from ui.embeds import test_start_embed, test_result_embed
from ui.views import TestSession, TestStartView
from utils.helpers import is_opiekun, is_moderator

if TYPE_CHECKING:
    from bot import LearningBot


class TestsCog(commands.Cog):
    test = app_commands.Group(name="test", description="System testów")

    def __init__(self, bot: LearningBot) -> None:
        self.bot = bot
        self.active_tests: dict[int, TestSession] = {}

    @test.command(name="start", description="Rozpocznij test")
    @app_commands.describe(
        kategoria="Kategoria pytań (puste = mix)",
        ilosc="Liczba pytań (domyślnie 10)",
        czas="Limit czasu w minutach (domyślnie 15)",
        trudnosc="Trudność 1-3 (puste = mix)",
    )
    async def start_test(
        self,
        interaction: discord.Interaction,
        kategoria: str | None = None,
        ilosc: int = 10,
        czas: int = 15,
        trudnosc: int | None = None,
    ) -> None:
        if not await is_moderator(interaction, self.bot.database):
            await interaction.response.send_message(
                "\u274c Brak uprawnień (wymagana rola Moderatora).", ephemeral=True
            )
            return

        if interaction.user.id in self.active_tests:
            await interaction.response.send_message(
                "\u274c Masz już aktywny test. Zakończ go najpierw.", ephemeral=True
            )
            return

        category_id = None
        category_name = None
        if kategoria:
            cat = await models.get_category_by_name(self.bot.database, kategoria)
            if cat:
                category_id = int(cat["id"])
                category_name = str(cat["name"])
            else:
                await interaction.response.send_message(
                    f"\u274c Nie znaleziono kategorii: {kategoria}", ephemeral=True
                )
                return

        abcde_count = max(1, int(ilosc * 0.7))
        descriptive_count = ilosc - abcde_count

        abcde_available = await models.count_questions(
            self.bot.database, category_id=category_id, q_type="abcde"
        )
        descriptive_available = await models.count_questions(
            self.bot.database, category_id=category_id, q_type="descriptive"
        )

        abcde_count = min(abcde_count, abcde_available)
        descriptive_count = min(descriptive_count, descriptive_available)

        if abcde_count + descriptive_count == 0:
            await interaction.response.send_message(
                "\u274c Brak pytań w bazie dla wybranych kryteriów.", ephemeral=True
            )
            return

        assert interaction.guild is not None
        instance_id = await models.create_test_instance(
            self.bot.database,
            user_id=str(interaction.user.id),
            guild_id=str(interaction.guild.id),
            time_limit_minutes=czas,
            passing_threshold=60,
            abcde_total=abcde_count,
            descriptive_total=descriptive_count,
        )

        abcde_questions = await models.get_random_questions(
            self.bot.database, "abcde", abcde_count,
            category_id=category_id, difficulty=trudnosc,
        )
        descriptive_questions = await models.get_random_questions(
            self.bot.database, "descriptive", descriptive_count,
            category_id=category_id, difficulty=trudnosc,
        )

        all_questions = abcde_questions + descriptive_questions
        random.shuffle(all_questions)

        user_id = interaction.user.id

        def cleanup() -> None:
            self.active_tests.pop(user_id, None)

        session = TestSession(
            db=self.bot.database,
            test_instance_id=instance_id,
            questions=all_questions,
            time_limit_minutes=czas,
            passing_threshold=60,
            on_finish=cleanup,
        )
        self.active_tests[user_id] = session

        embed = test_start_embed(
            instance_id,
            abcde_count,
            descriptive_count,
            czas,
            60,
            category_name,
        )
        start_view = TestStartView(session)
        await interaction.response.send_message(embed=embed, view=start_view, ephemeral=True)

        await start_view.wait()
        if not start_view.started:
            self.active_tests.pop(interaction.user.id, None)

    @test.command(name="moje", description="Moja historia testów")
    async def my_tests(self, interaction: discord.Interaction) -> None:
        if not await is_moderator(interaction, self.bot.database):
            await interaction.response.send_message(
                "\u274c Brak uprawnień.", ephemeral=True
            )
            return

        tests = await models.get_user_tests(self.bot.database, str(interaction.user.id))
        if not tests:
            await interaction.response.send_message(
                "Nie masz jeszcze żadnych testów.", ephemeral=True
            )
            return

        lines: list[str] = []
        for t in tests[:20]:
            status_emoji = {
                "in_progress": "\u23f3",
                "completed": "\U0001f4dd",
                "grading": "\u23f3",
                "graded": "\u2705" if t.get("passed") else "\u274c",
                "cancelled": "\u26d4",
            }.get(str(t["status"]), "\u2753")

            pct = f" — {t['total_percent']}%" if t.get("total_percent") is not None else ""
            lines.append(f"{status_emoji} Test **#{t['id']}** [{t['status']}]{pct}")

        embed = discord.Embed(
            title="\U0001f4dd Moje testy",
            description="\n".join(lines),
            color=discord.Color.blue(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @test.command(name="wynik", description="Szczegółowy wynik testu")
    @app_commands.describe(id_testu="ID testu")
    async def test_result(self, interaction: discord.Interaction, id_testu: int) -> None:
        instance = await models.get_test_instance(self.bot.database, id_testu)
        if not instance:
            await interaction.response.send_message(
                f"\u274c Nie znaleziono testu #{id_testu}.", ephemeral=True
            )
            return

        is_own = str(interaction.user.id) == str(instance["user_id"])
        is_admin = await is_opiekun(interaction, self.bot.database)
        if not is_own and not is_admin:
            await interaction.response.send_message(
                "\u274c Brak uprawnień do przeglądania tego testu.", ephemeral=True
            )
            return

        has_ungraded = str(instance["status"]) in ("grading", "completed")
        embed = test_result_embed(
            id_testu,
            int(instance.get("abcde_score") or 0),
            int(instance.get("abcde_total") or 0),
            int(instance.get("descriptive_score") or 0),
            int(instance.get("descriptive_total") or 0),
            float(instance["total_percent"]) if instance.get("total_percent") is not None else None,
            bool(instance.get("passed")) if instance.get("passed") is not None else None,
            has_ungraded=has_ungraded,
        )

        answers = await models.get_test_answers(self.bot.database, id_testu)
        details: list[str] = []
        for a in answers:
            q_type = "ABCDE" if a["question_type"] == "abcde" else "Opisowe"
            if a["is_correct"] == 1:
                status = "\u2705"
            elif a["is_correct"] == 0:
                status = "\u274c"
            else:
                status = "\u23f3"
            pts = f"{a.get('points_awarded', '?')}/{a.get('max_points', '?')}"
            details.append(f"{status} [{q_type}] {pts}")
            if a.get("admin_comment"):
                details.append(f"   \U0001f4ac {a['admin_comment']}")

        if details:
            embed.add_field(
                name="Szczegóły odpowiedzi",
                value="\n".join(details[:20]),
                inline=False,
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @test.command(name="szablon", description="Stwórz szablon testu (Opiekun)")
    @app_commands.describe(
        nazwa="Nazwa szablonu",
        abcde="Liczba pytań ABCDE",
        opisowe="Liczba pytań opisowych",
        kategoria="Kategoria (puste = mix)",
        czas="Limit czasu w minutach",
        prog="Próg zaliczenia (%)",
    )
    async def create_template(
        self,
        interaction: discord.Interaction,
        nazwa: str,
        abcde: int = 7,
        opisowe: int = 3,
        kategoria: str | None = None,
        czas: int = 15,
        prog: int = 60,
    ) -> None:
        if not await is_opiekun(interaction, self.bot.database):
            await interaction.response.send_message(
                "\u274c Brak uprawnień (wymagana rola Opiekuna).", ephemeral=True
            )
            return

        category_id = None
        if kategoria:
            cat = await models.get_category_by_name(self.bot.database, kategoria)
            if cat:
                category_id = int(cat["id"])

        template_id = await models.create_test_template(
            self.bot.database,
            name=nazwa,
            abcde_count=abcde,
            descriptive_count=opisowe,
            time_limit_minutes=czas,
            passing_threshold=prog,
            category_id=category_id,
            created_by=str(interaction.user.id),
        )
        await interaction.response.send_message(
            f"\u2705 Szablon **{nazwa}** (#{template_id}) utworzony.\n"
            f"Pytania: {abcde} ABCDE + {opisowe} opisowe | Czas: {czas}min | Próg: {prog}%",
            ephemeral=True,
        )

    @test.command(name="szablony", description="Lista szablonów testów (Opiekun)")
    async def list_templates(self, interaction: discord.Interaction) -> None:
        if not await is_opiekun(interaction, self.bot.database):
            await interaction.response.send_message(
                "\u274c Brak uprawnień.", ephemeral=True
            )
            return

        templates = await models.get_test_templates(self.bot.database)
        if not templates:
            await interaction.response.send_message(
                "Brak szablonów testów.", ephemeral=True
            )
            return

        lines: list[str] = []
        for t in templates:
            lines.append(
                f"**#{t['id']}** {t['name']} — "
                f"{t['abcde_count']} ABCDE + {t['descriptive_count']} opisowe | "
                f"{t['time_limit_minutes']}min | Próg: {t['passing_threshold']}%"
            )

        embed = discord.Embed(
            title="\U0001f4cb Szablony testów",
            description="\n".join(lines),
            color=discord.Color.blue(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @test.command(name="przypisz", description="Przypisz test moderatorowi (Opiekun)")
    @app_commands.describe(szablon_id="ID szablonu", user="Moderator")
    async def assign_test(
        self,
        interaction: discord.Interaction,
        szablon_id: int,
        user: discord.Member,
    ) -> None:
        if not await is_opiekun(interaction, self.bot.database):
            await interaction.response.send_message(
                "\u274c Brak uprawnień.", ephemeral=True
            )
            return

        template = await models.get_test_template(self.bot.database, szablon_id)
        if not template:
            await interaction.response.send_message(
                f"\u274c Nie znaleziono szablonu #{szablon_id}.", ephemeral=True
            )
            return

        try:
            await user.send(
                f"\U0001f4dd Masz nowy test do wykonania: **{template['name']}**\n"
                f"Pytania: {template['abcde_count']} ABCDE + {template['descriptive_count']} opisowe\n"
                f"Czas: {template['time_limit_minutes']} minut | Próg: {template['passing_threshold']}%\n\n"
                f"Użyj `/test start` na serwerze aby rozpocząć."
            )
            await interaction.response.send_message(
                f"\u2705 Test **{template['name']}** przypisany do {user.mention}. Powiadomienie wysłane DM.",
                ephemeral=True,
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                f"\u26a0\ufe0f Test przypisany, ale nie mogłem wysłać DM do {user.mention} (DM wyłączone).",
                ephemeral=True,
            )

    @test.command(name="oczekujace", description="Testy oczekujące na ocenę (Opiekun)")
    async def pending_tests(self, interaction: discord.Interaction) -> None:
        if not await is_opiekun(interaction, self.bot.database):
            await interaction.response.send_message(
                "\u274c Brak uprawnień.", ephemeral=True
            )
            return

        guild_id = str(interaction.guild.id) if interaction.guild else None
        pending = await models.get_pending_grading_tests(self.bot.database, guild_id)
        if not pending:
            await interaction.response.send_message(
                "\u2705 Brak testów oczekujących na ocenę.", ephemeral=True
            )
            return

        lines: list[str] = []
        for t in pending:
            lines.append(
                f"\u23f3 Test **#{t['id']}** — <@{t['user_id']}> | "
                f"ABCDE: {t.get('abcde_score', 0)}/{t.get('abcde_total', 0)}"
            )

        embed = discord.Embed(
            title=f"\u23f3 Testy oczekujące na ocenę ({len(pending)})",
            description="\n".join(lines),
            color=discord.Color.orange(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: LearningBot) -> None:
    await bot.add_cog(TestsCog(bot))
