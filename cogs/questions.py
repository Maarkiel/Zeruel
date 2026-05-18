from __future__ import annotations

import json
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from database import models
from ui.embeds import question_preview_embed
from ui.modals import AddABCDEModal, AddDescriptiveModal, EditQuestionModal
from utils.helpers import is_opiekun

if TYPE_CHECKING:
    from bot import LearningBot


class CategorySelect(discord.ui.Select["CategorySelectView"]):
    def __init__(self, categories: list[dict[str, object]], action: str) -> None:
        self.action = action
        options = [
            discord.SelectOption(label=str(c["name"]), value=str(c["id"]))
            for c in categories[:25]
        ]
        super().__init__(placeholder="Wybierz kategorię...", options=options)

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        self.view.selected_id = int(self.values[0])
        self.view.selected_name = next(
            (o.label for o in self.options if o.value == self.values[0]), ""
        )
        self.view.stop()
        await interaction.response.defer()


class CategorySelectView(discord.ui.View):
    def __init__(self, categories: list[dict[str, object]], action: str) -> None:
        super().__init__(timeout=60)
        self.selected_id: int | None = None
        self.selected_name: str = ""
        self.add_item(CategorySelect(categories, action))


class QuestionsCog(commands.Cog):
    pytanie = app_commands.Group(name="pytanie", description="Zarządzanie bazą pytań")
    kategoria = app_commands.Group(name="kategoria", description="Zarządzanie kategoriami")

    def __init__(self, bot: LearningBot) -> None:
        self.bot = bot

    @pytanie.command(name="dodaj-abcde", description="Dodaj nowe pytanie ABCDE")
    async def add_abcde(self, interaction: discord.Interaction) -> None:
        if not await is_opiekun(interaction, self.bot.database):
            await interaction.response.send_message(
                "\u274c Brak uprawnień (wymagana rola Opiekuna).", ephemeral=True
            )
            return

        categories = await models.get_categories(self.bot.database)
        if not categories:
            await interaction.response.send_message(
                "\u274c Brak kategorii. Najpierw dodaj kategorię: `/kategoria dodaj`",
                ephemeral=True,
            )
            return

        view = CategorySelectView(categories, "abcde")
        await interaction.response.send_message(
            "Wybierz kategorię dla pytania:", view=view, ephemeral=True
        )
        await view.wait()

        if view.selected_id is None:
            return

        modal = AddABCDEModal(view.selected_id, view.selected_name)
        # We need a new interaction for the modal - use followup approach
        # Actually, re-send with modal on a button click
        await self._show_abcde_modal(interaction, view.selected_id, view.selected_name)

    async def _show_abcde_modal(
        self, interaction: discord.Interaction, category_id: int, category_name: str
    ) -> None:
        modal = AddABCDEModal(category_id, category_name)

        class ModalTriggerView(discord.ui.View):
            def __init__(self) -> None:
                super().__init__(timeout=60)

            @discord.ui.button(label="Wypełnij formularz", style=discord.ButtonStyle.primary)
            async def open_modal(
                self_btn, btn_interaction: discord.Interaction, button: discord.ui.Button
            ) -> None:
                await btn_interaction.response.send_modal(modal)

        trigger_view = ModalTriggerView()
        await interaction.edit_original_response(
            content=f"Kategoria: **{category_name}** — kliknij przycisk aby wypełnić formularz:",
            view=trigger_view,
        )
        await modal.wait()

        if modal.result is None:
            return

        question_id = await models.create_question(
            self.bot.database,
            category_id=category_id,
            q_type="abcde",
            content=str(modal.result["content"]),
            options=modal.result["options"] if isinstance(modal.result["options"], list) else None,
            correct_answer=str(modal.result["correct_answer"]),
            explanation=str(modal.result["explanation"]) if modal.result.get("explanation") else None,
            max_points=1,
            difficulty=1,
            created_by=str(interaction.user.id),
        )
        await interaction.edit_original_response(
            content=f"\u2705 Pytanie ABCDE **#{question_id}** dodane do kategorii **{category_name}**.",
            view=None,
        )

    @pytanie.command(name="dodaj-opisowe", description="Dodaj nowe pytanie opisowe")
    async def add_descriptive(self, interaction: discord.Interaction) -> None:
        if not await is_opiekun(interaction, self.bot.database):
            await interaction.response.send_message(
                "\u274c Brak uprawnień (wymagana rola Opiekuna).", ephemeral=True
            )
            return

        categories = await models.get_categories(self.bot.database)
        if not categories:
            await interaction.response.send_message(
                "\u274c Brak kategorii. Najpierw dodaj kategorię: `/kategoria dodaj`",
                ephemeral=True,
            )
            return

        view = CategorySelectView(categories, "descriptive")
        await interaction.response.send_message(
            "Wybierz kategorię dla pytania:", view=view, ephemeral=True
        )
        await view.wait()

        if view.selected_id is None:
            return

        await self._show_descriptive_modal(interaction, view.selected_id, view.selected_name)

    async def _show_descriptive_modal(
        self, interaction: discord.Interaction, category_id: int, category_name: str
    ) -> None:
        modal = AddDescriptiveModal(category_id, category_name)

        class ModalTriggerView(discord.ui.View):
            def __init__(self) -> None:
                super().__init__(timeout=60)

            @discord.ui.button(label="Wypełnij formularz", style=discord.ButtonStyle.primary)
            async def open_modal(
                self_btn, btn_interaction: discord.Interaction, button: discord.ui.Button
            ) -> None:
                await btn_interaction.response.send_modal(modal)

        trigger_view = ModalTriggerView()
        await interaction.edit_original_response(
            content=f"Kategoria: **{category_name}** — kliknij przycisk aby wypełnić formularz:",
            view=trigger_view,
        )
        await modal.wait()

        if modal.result is None:
            return

        question_id = await models.create_question(
            self.bot.database,
            category_id=category_id,
            q_type="descriptive",
            content=str(modal.result["content"]),
            model_answer=str(modal.result["model_answer"]),
            max_points=int(modal.result["max_points"]),  # type: ignore[arg-type]
            difficulty=1,
            created_by=str(interaction.user.id),
        )
        await interaction.edit_original_response(
            content=f"\u2705 Pytanie opisowe **#{question_id}** dodane do kategorii **{category_name}**.",
            view=None,
        )

    @pytanie.command(name="lista", description="Lista pytań")
    @app_commands.describe(
        kategoria="Filtr kategorii",
        typ="Typ pytania",
        trudnosc="Trudność (1-3)",
    )
    @app_commands.choices(
        typ=[
            app_commands.Choice(name="ABCDE", value="abcde"),
            app_commands.Choice(name="Opisowe", value="descriptive"),
        ]
    )
    async def list_questions(
        self,
        interaction: discord.Interaction,
        kategoria: str | None = None,
        typ: str | None = None,
        trudnosc: int | None = None,
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

        questions = await models.get_questions(
            self.bot.database,
            category_id=category_id,
            q_type=typ,
            difficulty=trudnosc,
        )

        if not questions:
            await interaction.response.send_message(
                "Brak pytań spełniających kryteria.", ephemeral=True
            )
            return

        lines: list[str] = []
        for q in questions[:25]:
            q_type = "ABCDE" if q["type"] == "abcde" else "Opisowe"
            lines.append(
                f"**#{q['id']}** [{q_type}] {str(q['content'])[:60]}..."
            )

        embed = discord.Embed(
            title=f"\U0001f4cb Lista pytań ({len(questions)})",
            description="\n".join(lines),
            color=discord.Color.blue(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @pytanie.command(name="podglad", description="Podgląd pytania z odpowiedzią")
    @app_commands.describe(id="ID pytania")
    async def preview_question(self, interaction: discord.Interaction, id: int) -> None:
        if not await is_opiekun(interaction, self.bot.database):
            await interaction.response.send_message(
                "\u274c Brak uprawnień.", ephemeral=True
            )
            return

        question = await models.get_question(self.bot.database, id)
        if not question:
            await interaction.response.send_message(
                f"\u274c Nie znaleziono pytania #{id}.", ephemeral=True
            )
            return

        embed = question_preview_embed(question)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @pytanie.command(name="edytuj", description="Edytuj pytanie")
    @app_commands.describe(id="ID pytania")
    async def edit_question(self, interaction: discord.Interaction, id: int) -> None:
        if not await is_opiekun(interaction, self.bot.database):
            await interaction.response.send_message(
                "\u274c Brak uprawnień.", ephemeral=True
            )
            return

        question = await models.get_question(self.bot.database, id)
        if not question:
            await interaction.response.send_message(
                f"\u274c Nie znaleziono pytania #{id}.", ephemeral=True
            )
            return

        modal = EditQuestionModal(question)
        await interaction.response.send_modal(modal)
        await modal.wait()

        if modal.result is None:
            return

        await models.update_question(self.bot.database, id, **modal.result)
        await interaction.followup.send(
            f"\u2705 Pytanie **#{id}** zaktualizowane.", ephemeral=True
        )

    @pytanie.command(name="usun", description="Usuń pytanie (dezaktywuj)")
    @app_commands.describe(id="ID pytania")
    async def delete_question(self, interaction: discord.Interaction, id: int) -> None:
        if not await is_opiekun(interaction, self.bot.database):
            await interaction.response.send_message(
                "\u274c Brak uprawnień.", ephemeral=True
            )
            return

        question = await models.get_question(self.bot.database, id)
        if not question:
            await interaction.response.send_message(
                f"\u274c Nie znaleziono pytania #{id}.", ephemeral=True
            )
            return

        await models.delete_question(self.bot.database, id)
        await interaction.response.send_message(
            f"\u2705 Pytanie **#{id}** dezaktywowane.", ephemeral=True
        )

    @pytanie.command(name="import", description="Import pytań z JSON")
    @app_commands.describe(plik="Plik JSON z pytaniami")
    async def import_questions(
        self, interaction: discord.Interaction, plik: discord.Attachment
    ) -> None:
        if not await is_opiekun(interaction, self.bot.database):
            await interaction.response.send_message(
                "\u274c Brak uprawnień.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        data = await plik.read()
        try:
            questions = json.loads(data)
        except json.JSONDecodeError:
            await interaction.followup.send("\u274c Nieprawidłowy format JSON.", ephemeral=True)
            return

        if not isinstance(questions, list):
            await interaction.followup.send(
                "\u274c JSON musi zawierać listę pytań.", ephemeral=True
            )
            return

        imported = 0
        for q in questions:
            cat_name = q.get("category", "Ogólne")
            cat = await models.get_category_by_name(self.bot.database, cat_name)
            if not cat:
                cat_id = await models.create_category(self.bot.database, cat_name)
            else:
                cat_id = int(cat["id"])

            await models.create_question(
                self.bot.database,
                category_id=cat_id,
                q_type=q.get("type", "abcde"),
                content=q.get("content", ""),
                options=q.get("options"),
                correct_answer=q.get("correct_answer"),
                model_answer=q.get("model_answer"),
                explanation=q.get("explanation"),
                max_points=q.get("max_points", 1),
                difficulty=q.get("difficulty", 1),
                created_by=str(interaction.user.id),
            )
            imported += 1

        await interaction.followup.send(
            f"\u2705 Zaimportowano **{imported}** pytań.", ephemeral=True
        )

    @pytanie.command(name="eksport", description="Eksport pytań do JSON")
    @app_commands.describe(kategoria="Kategoria do eksportu (puste = wszystkie)")
    async def export_questions(
        self, interaction: discord.Interaction, kategoria: str | None = None
    ) -> None:
        if not await is_opiekun(interaction, self.bot.database):
            await interaction.response.send_message(
                "\u274c Brak uprawnień.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        category_id = None
        if kategoria:
            cat = await models.get_category_by_name(self.bot.database, kategoria)
            if cat:
                category_id = int(cat["id"])

        questions = await models.get_questions(
            self.bot.database, category_id=category_id
        )

        export_data = []
        categories_cache: dict[int, str] = {}
        for q in questions:
            cat_id = int(q["category_id"])
            if cat_id not in categories_cache:
                cat = await models.get_category(self.bot.database, cat_id)
                categories_cache[cat_id] = str(cat["name"]) if cat else "Unknown"

            export_data.append({
                "type": q["type"],
                "category": categories_cache[cat_id],
                "content": q["content"],
                "options": q.get("options"),
                "correct_answer": q.get("correct_answer"),
                "model_answer": q.get("model_answer"),
                "explanation": q.get("explanation"),
                "max_points": q.get("max_points"),
                "difficulty": q.get("difficulty"),
            })

        json_str = json.dumps(export_data, ensure_ascii=False, indent=2)
        file = discord.File(
            fp=__import__("io").BytesIO(json_str.encode("utf-8")),
            filename="pytania_export.json",
        )
        await interaction.followup.send(
            f"\u2705 Eksport **{len(export_data)}** pytań:", file=file, ephemeral=True
        )

    # ---- Kategorie ----

    @kategoria.command(name="dodaj", description="Dodaj nową kategorię")
    @app_commands.describe(nazwa="Nazwa kategorii", opis="Opis (opcjonalny)")
    async def add_category(
        self, interaction: discord.Interaction, nazwa: str, opis: str | None = None
    ) -> None:
        if not await is_opiekun(interaction, self.bot.database):
            await interaction.response.send_message(
                "\u274c Brak uprawnień.", ephemeral=True
            )
            return

        existing = await models.get_category_by_name(self.bot.database, nazwa)
        if existing:
            await interaction.response.send_message(
                f"\u274c Kategoria **{nazwa}** już istnieje.", ephemeral=True
            )
            return

        cat_id = await models.create_category(self.bot.database, nazwa, opis)
        await interaction.response.send_message(
            f"\u2705 Kategoria **{nazwa}** (#{cat_id}) dodana.", ephemeral=True
        )

    @kategoria.command(name="lista", description="Lista kategorii")
    async def list_categories(self, interaction: discord.Interaction) -> None:
        categories = await models.get_categories(self.bot.database)
        if not categories:
            await interaction.response.send_message(
                "Brak kategorii.", ephemeral=True
            )
            return

        lines: list[str] = []
        for c in categories:
            count = await models.count_questions(self.bot.database, int(c["id"]))
            desc = f" — {c['description']}" if c.get("description") else ""
            lines.append(f"**#{c['id']}** {c['name']}{desc} ({count} pytań)")

        embed = discord.Embed(
            title="\U0001f4c1 Kategorie",
            description="\n".join(lines),
            color=discord.Color.blue(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @kategoria.command(name="edytuj", description="Zmień nazwę kategorii")
    @app_commands.describe(id="ID kategorii", nazwa="Nowa nazwa")
    async def edit_category(
        self, interaction: discord.Interaction, id: int, nazwa: str
    ) -> None:
        if not await is_opiekun(interaction, self.bot.database):
            await interaction.response.send_message(
                "\u274c Brak uprawnień.", ephemeral=True
            )
            return

        cat = await models.get_category(self.bot.database, id)
        if not cat:
            await interaction.response.send_message(
                f"\u274c Nie znaleziono kategorii #{id}.", ephemeral=True
            )
            return

        await models.update_category(self.bot.database, id, nazwa)
        await interaction.response.send_message(
            f"\u2705 Kategoria **#{id}** zmieniona na **{nazwa}**.", ephemeral=True
        )

    @kategoria.command(name="usun", description="Usuń kategorię (jeśli pusta)")
    @app_commands.describe(id="ID kategorii")
    async def delete_category(self, interaction: discord.Interaction, id: int) -> None:
        if not await is_opiekun(interaction, self.bot.database):
            await interaction.response.send_message(
                "\u274c Brak uprawnień.", ephemeral=True
            )
            return

        success = await models.delete_category(self.bot.database, id)
        if success:
            await interaction.response.send_message(
                f"\u2705 Kategoria **#{id}** usunięta.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"\u274c Kategoria **#{id}** zawiera pytania — najpierw je usuń.",
                ephemeral=True,
            )


async def setup(bot: LearningBot) -> None:
    await bot.add_cog(QuestionsCog(bot))
