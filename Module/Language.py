# I'm going to use the discord.py module for creating a discord bot. https://github.com/Rapptz/discord.py
# Asyncio is required to interact with the discord bot. asyncio.sleep() is useful as well.
import discord
import asyncio


class LanguageBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


# This class manages the entire language as well as the discord bot.
class LanguageManager:

    def __init__(self, bot_token):
        self.bot_token = bot_token
        self.bot = None

    async def start_bot(self):
        self.bot = LanguageBot()  # Construct Bot
        print("Bot Made")
        asyncio.get_event_loop().create_task(self.bot.start(self.bot_token))
        print("Bot Started")
        await self.bot.wait_until_ready()
        print("Bot Ready")

    async def stop_bot(self):
        if self.bot is not None:
            asyncio.get_event_loop().run_until_complete(self.bot.close())


lm = LanguageManager("token")
asyncio.get_event_loop().run_until_complete(lm.start_bot())
print("Returned.")
