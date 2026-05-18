from __future__ import annotations

import logging

import discord
from discord.ext import commands

from config import DISCORD_TOKEN, OWNER_ID, LOG_LEVEL
from database.connection import Database

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("zeruel")

COGS = [
    "cogs.questions",
    "cogs.tests",
    "cogs.grading",
    "cogs.study",
    "cogs.stats",
    "cogs.config",
]


class LearningBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(
            command_prefix="!",
            intents=intents,
            owner_id=OWNER_ID,
        )
        self.database = Database()

    async def setup_hook(self) -> None:
        await self.database.connect()
        logger.info("Baza danych połączona: %s", self.database.path)

        for cog in COGS:
            try:
                await self.load_extension(cog)
                logger.info("Załadowano cog: %s", cog)
            except Exception:
                logger.exception("Błąd ładowania cog: %s", cog)

        if self.owner_id:
            guild = discord.Object(id=0)  # sync globally on first run
            self.tree.copy_global_to(guild=guild)
        logger.info("Komendy slash gotowe do synchronizacji (użyj !sync na serwerze).")

    async def on_ready(self) -> None:
        assert self.user is not None
        logger.info("Bot zalogowany jako: %s (ID: %s)", self.user, self.user.id)
        synced = await self.tree.sync()
        logger.info("Zsynchronizowano %d komend slash.", len(synced))
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="moderatorów się uczących",
            )
        )

    async def close(self) -> None:
        await self.database.close()
        await super().close()


def main() -> None:
    if not DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN nie jest ustawiony! Sprawdź plik .env")
        return
    bot = LearningBot()
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()
