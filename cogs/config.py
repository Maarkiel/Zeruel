from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from database import models
from utils.helpers import is_owner

if TYPE_CHECKING:
    from bot import LearningBot


class ConfigCog(commands.Cog):
    config = app_commands.Group(name="config", description="Konfiguracja bota (Owner)")

    def __init__(self, bot: LearningBot) -> None:
        self.bot = bot

    @config.command(name="kanal-oceny", description="Ustaw kanał powiadomień o ocenach")
    @app_commands.describe(kanal="Kanał na powiadomienia")
    async def set_grading_channel(
        self, interaction: discord.Interaction, kanal: discord.TextChannel
    ) -> None:
        if not await is_owner(interaction):
            await interaction.response.send_message(
                "\u274c Tylko Owner może zmieniać konfigurację.", ephemeral=True
            )
            return

        assert interaction.guild is not None
        await models.update_guild_config(
            self.bot.database, str(interaction.guild.id),
            grading_channel_id=str(kanal.id),
        )
        await interaction.response.send_message(
            f"\u2705 Kanał ocen ustawiony na {kanal.mention}.", ephemeral=True
        )

    @config.command(name="kanal-wynikow", description="Ustaw kanał wyników testów")
    @app_commands.describe(kanal="Kanał na wyniki")
    async def set_results_channel(
        self, interaction: discord.Interaction, kanal: discord.TextChannel
    ) -> None:
        if not await is_owner(interaction):
            await interaction.response.send_message(
                "\u274c Tylko Owner może zmieniać konfigurację.", ephemeral=True
            )
            return

        assert interaction.guild is not None
        await models.update_guild_config(
            self.bot.database, str(interaction.guild.id),
            test_results_channel_id=str(kanal.id),
        )
        await interaction.response.send_message(
            f"\u2705 Kanał wyników ustawiony na {kanal.mention}.", ephemeral=True
        )

    @config.command(name="rola-opiekun", description="Ustaw rolę Opiekuna")
    @app_commands.describe(rola="Rola Opiekuna")
    async def set_admin_role(
        self, interaction: discord.Interaction, rola: discord.Role
    ) -> None:
        if not await is_owner(interaction):
            await interaction.response.send_message(
                "\u274c Tylko Owner może zmieniać konfigurację.", ephemeral=True
            )
            return

        assert interaction.guild is not None
        await models.update_guild_config(
            self.bot.database, str(interaction.guild.id),
            admin_role_id=str(rola.id),
        )
        await interaction.response.send_message(
            f"\u2705 Rola Opiekuna ustawiona na {rola.mention}.", ephemeral=True
        )

    @config.command(name="rola-moderator", description="Ustaw rolę Moderatora")
    @app_commands.describe(rola="Rola Moderatora")
    async def set_mod_role(
        self, interaction: discord.Interaction, rola: discord.Role
    ) -> None:
        if not await is_owner(interaction):
            await interaction.response.send_message(
                "\u274c Tylko Owner może zmieniać konfigurację.", ephemeral=True
            )
            return

        assert interaction.guild is not None
        await models.update_guild_config(
            self.bot.database, str(interaction.guild.id),
            moderator_role_id=str(rola.id),
        )
        await interaction.response.send_message(
            f"\u2705 Rola Moderatora ustawiona na {rola.mention}.", ephemeral=True
        )

    @config.command(name="pokaz", description="Pokaż aktualną konfigurację")
    async def show_config(self, interaction: discord.Interaction) -> None:
        if not await is_owner(interaction):
            await interaction.response.send_message(
                "\u274c Tylko Owner może przeglądać konfigurację.", ephemeral=True
            )
            return

        assert interaction.guild is not None
        cfg = await models.get_guild_config(
            self.bot.database, str(interaction.guild.id)
        )

        embed = discord.Embed(
            title="\u2699\ufe0f Konfiguracja",
            color=discord.Color.greyple(),
        )

        grading_ch = f"<#{cfg['grading_channel_id']}>" if cfg.get("grading_channel_id") else "Nie ustawiony"
        results_ch = f"<#{cfg['test_results_channel_id']}>" if cfg.get("test_results_channel_id") else "Nie ustawiony"
        admin_role = f"<@&{cfg['admin_role_id']}>" if cfg.get("admin_role_id") else "Nie ustawiona"
        mod_role = f"<@&{cfg['moderator_role_id']}>" if cfg.get("moderator_role_id") else "Nie ustawiona"

        embed.add_field(name="Kanał ocen", value=grading_ch, inline=True)
        embed.add_field(name="Kanał wyników", value=results_ch, inline=True)
        embed.add_field(name="Rola Opiekuna", value=admin_role, inline=True)
        embed.add_field(name="Rola Moderatora", value=mod_role, inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: LearningBot) -> None:
    await bot.add_cog(ConfigCog(bot))
