from __future__ import annotations

import discord


class AddABCDEModal(discord.ui.Modal):
    """Modal for adding an ABCDE question."""

    def __init__(self, category_id: int, category_name: str) -> None:
        super().__init__(title=f"Nowe pytanie ABCDE — {category_name}")
        self.category_id = category_id

        self.content_input = discord.ui.TextInput(
            label="Treść pytania",
            style=discord.TextStyle.paragraph,
            placeholder="Wpisz treść pytania...",
            max_length=1000,
            required=True,
        )
        self.options_input = discord.ui.TextInput(
            label="Opcje (jedna na linię, np. A: odpowiedź)",
            style=discord.TextStyle.paragraph,
            placeholder="A: pierwsza opcja\nB: druga opcja\nC: trzecia opcja",
            max_length=1000,
            required=True,
        )
        self.correct_input = discord.ui.TextInput(
            label="Poprawna odpowiedź (litera: A/B/C/D/E)",
            placeholder="B",
            max_length=1,
            required=True,
        )
        self.explanation_input = discord.ui.TextInput(
            label="Wyjaśnienie (opcjonalne)",
            style=discord.TextStyle.paragraph,
            placeholder="Wyjaśnienie dlaczego ta odpowiedź jest poprawna...",
            max_length=1000,
            required=False,
        )

        self.add_item(self.content_input)
        self.add_item(self.options_input)
        self.add_item(self.correct_input)
        self.add_item(self.explanation_input)

        self.result: dict[str, object] | None = None

    async def on_submit(self, interaction: discord.Interaction) -> None:
        options = [
            line.strip()
            for line in self.options_input.value.strip().split("\n")
            if line.strip()
        ]
        correct = self.correct_input.value.strip().upper()

        if len(options) < 2:
            await interaction.response.send_message(
                "\u274c Musisz podać minimum 2 opcje.", ephemeral=True
            )
            return

        valid_letters = [opt.split(":")[0].strip().upper() for opt in options]
        if correct not in valid_letters:
            await interaction.response.send_message(
                f"\u274c Poprawna odpowiedź '{correct}' nie jest wśród opcji: {', '.join(valid_letters)}",
                ephemeral=True,
            )
            return

        self.result = {
            "content": self.content_input.value.strip(),
            "options": options,
            "correct_answer": correct,
            "explanation": self.explanation_input.value.strip() if self.explanation_input.value else None,
        }
        await interaction.response.defer()


class AddDescriptiveModal(discord.ui.Modal):
    """Modal for adding a descriptive question."""

    def __init__(self, category_id: int, category_name: str) -> None:
        super().__init__(title=f"Nowe pytanie opisowe — {category_name}")
        self.category_id = category_id

        self.content_input = discord.ui.TextInput(
            label="Treść pytania",
            style=discord.TextStyle.paragraph,
            placeholder="Wpisz treść pytania / scenariusz...",
            max_length=1000,
            required=True,
        )
        self.model_answer_input = discord.ui.TextInput(
            label="Wzorcowa odpowiedź (do oceny)",
            style=discord.TextStyle.paragraph,
            placeholder="Opis wzorcowej odpowiedzi...",
            max_length=1000,
            required=True,
        )
        self.max_points_input = discord.ui.TextInput(
            label="Maks. punktów",
            placeholder="10",
            max_length=3,
            required=True,
            default="10",
        )

        self.add_item(self.content_input)
        self.add_item(self.model_answer_input)
        self.add_item(self.max_points_input)

        self.result: dict[str, object] | None = None

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            max_points = int(self.max_points_input.value.strip())
        except ValueError:
            await interaction.response.send_message(
                "\u274c Maks. punktów musi być liczbą.", ephemeral=True
            )
            return

        self.result = {
            "content": self.content_input.value.strip(),
            "model_answer": self.model_answer_input.value.strip(),
            "max_points": max_points,
        }
        await interaction.response.defer()


class EditQuestionModal(discord.ui.Modal):
    """Modal for editing an existing question."""

    def __init__(self, question: dict[str, object]) -> None:
        q_type = "ABCDE" if question["type"] == "abcde" else "Opisowe"
        super().__init__(title=f"Edycja pytania #{question['id']} ({q_type})")
        self.question = question

        self.content_input = discord.ui.TextInput(
            label="Treść pytania",
            style=discord.TextStyle.paragraph,
            default=str(question["content"]),
            max_length=1000,
            required=True,
        )
        self.add_item(self.content_input)

        if question["type"] == "abcde":
            options = question.get("options", [])
            options_text = "\n".join(options) if isinstance(options, list) else ""
            self.options_input = discord.ui.TextInput(
                label="Opcje (jedna na linię)",
                style=discord.TextStyle.paragraph,
                default=options_text,
                max_length=1000,
                required=True,
            )
            self.correct_input = discord.ui.TextInput(
                label="Poprawna odpowiedź (litera)",
                default=str(question.get("correct_answer", "")),
                max_length=1,
                required=True,
            )
            self.explanation_input = discord.ui.TextInput(
                label="Wyjaśnienie (opcjonalne)",
                style=discord.TextStyle.paragraph,
                default=str(question.get("explanation", "") or ""),
                max_length=1000,
                required=False,
            )
            self.add_item(self.options_input)
            self.add_item(self.correct_input)
            self.add_item(self.explanation_input)
        else:
            self.model_answer_input = discord.ui.TextInput(
                label="Wzorcowa odpowiedź",
                style=discord.TextStyle.paragraph,
                default=str(question.get("model_answer", "") or ""),
                max_length=1000,
                required=True,
            )
            self.max_points_input = discord.ui.TextInput(
                label="Maks. punktów",
                default=str(question.get("max_points", 10)),
                max_length=3,
                required=True,
            )
            self.add_item(self.model_answer_input)
            self.add_item(self.max_points_input)

        self.result: dict[str, object] | None = None

    async def on_submit(self, interaction: discord.Interaction) -> None:
        result: dict[str, object] = {"content": self.content_input.value.strip()}

        if self.question["type"] == "abcde":
            options = [
                line.strip()
                for line in self.options_input.value.strip().split("\n")
                if line.strip()
            ]
            correct = self.correct_input.value.strip().upper()
            result["options"] = options
            result["correct_answer"] = correct
            result["explanation"] = self.explanation_input.value.strip() if self.explanation_input.value else None
        else:
            try:
                max_points = int(self.max_points_input.value.strip())
            except ValueError:
                await interaction.response.send_message(
                    "\u274c Maks. punktów musi być liczbą.", ephemeral=True
                )
                return
            result["model_answer"] = self.model_answer_input.value.strip()
            result["max_points"] = max_points

        self.result = result
        await interaction.response.defer()
