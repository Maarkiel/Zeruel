from __future__ import annotations

import discord
from config import OWNER_ID
from database.models import get_guild_config

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from database.connection import Database


def difficulty_stars(level: int) -> str:
    return "\u2b50" * level


def progress_bar(current: int, total: int, length: int = 10) -> str:
    if total == 0:
        return "\u2591" * length
    filled = int(current / total * length)
    return "\u2588" * filled + "\u2591" * (length - filled)


def truncate(text: str, max_len: int = 100) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


async def is_owner(interaction: discord.Interaction) -> bool:
    return interaction.user.id == OWNER_ID


async def is_opiekun(interaction: discord.Interaction, db: Database) -> bool:
    if interaction.user.id == OWNER_ID:
        return True
    if interaction.guild is None:
        return False
    config = await get_guild_config(db, str(interaction.guild.id))
    admin_role_id = config.get("admin_role_id")
    if admin_role_id and isinstance(interaction.user, discord.Member):
        return any(str(r.id) == str(admin_role_id) for r in interaction.user.roles)
    return False


async def is_moderator(interaction: discord.Interaction, db: Database) -> bool:
    if await is_opiekun(interaction, db):
        return True
    if interaction.guild is None:
        return False
    config = await get_guild_config(db, str(interaction.guild.id))
    mod_role_id = config.get("moderator_role_id")
    if mod_role_id and isinstance(interaction.user, discord.Member):
        return any(str(r.id) == str(mod_role_id) for r in interaction.user.roles)
    return False
