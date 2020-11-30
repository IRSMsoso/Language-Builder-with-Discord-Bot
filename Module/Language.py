# I'm going to use the discord.py module for creating a discord bot. https://github.com/Rapptz/discord.py
# Asyncio is required to interact with the discord bot. asyncio.sleep() is useful as well. After these are included, it's easier to write the entire program asynchronously.
# Pickle is used for saving languages to binary file.
import discord
import asyncio
import pickle


class LanguageBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def on_message(self):


class Word:

    def __init__(self, text, pronunciation, definition, related_words=None):
        self.text = text
        self.pronunciation = pronunciation
        self.definition = definition
        if related_words is None:  # None is needed because of this: https://stackoverflow.com/questions/41686829/warning-about-mutable-default-argument-in-pycharm
            self.related_words = []
        else:
            self.related_words = related_words


class Sentence:

    def __init__(self, words):
        self.words = words


class Punctuation:

    def __init__(self, punctuation, usage):
        self.punctuation = punctuation
        self.usage = usage


class Language:

    def __init__(self, name="New Language"):
        self.punctuations = []
        self.words = []
        self.name = name
        self.channel = None


# This class manages the entire language as well as the discord bot.
class LanguageManager:

    def __init__(self, bot_token):
        self.bot_token = bot_token
        self.bot = None
        self.is_on = False

    async def run_manager(self):  # This is a blocking function that runs the entire program.
        self.is_on = True
        await self.start_bot()  # Start the bot.

        while self.is_on:  # Main Loop


        await self.stop_bot()

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

    async def shutdown_manager(self):
        self.is_on = False


lm = LanguageManager("token")
asyncio.get_event_loop().run_until_complete(lm.run_manager())
print("Returned.")
