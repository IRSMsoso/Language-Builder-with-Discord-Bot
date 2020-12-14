# I'm going to use the discord.py module for creating a discord bot. https://github.com/Rapptz/discord.py
# Asyncio is required to interact with the discord bot. asyncio.sleep() is useful as well. After these are included, it's easier to write the entire program asynchronously.
# Pickle is used for saving languages to binary file.
import discord
import asyncio
import pickle
from time import sleep


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


def get_command_list(full_command):
    original_command = full_command
    first_command_index = original_command.find('\"')
    if first_command_index == -1:  # There's a problem if there is no quotes in the command.
        print("Error, Something went wrong. Likely formatted incorrectly.")
        return None
    command_list = [original_command[:first_command_index]]  # Create a list of commands starting with the base command.
    command_list[0] = command_list[0].replace(' ', '')  # Replace any spaces since the first command can never have them.
    original_command = original_command[first_command_index:]  # Remove that first command from the rest of the string.
    print("Command List:")
    print(command_list)
    print("Original Command")
    print(original_command)
    while len(original_command) > 0:  # Until everything is drained form the string of commands.
        check_same = original_command
        command_list.append(original_command[1:original_command.find('\"', 1)])
        original_command = original_command[original_command.find('\"', 1) + 1:]
        original_command = original_command[original_command.find('\"'):]  # Get rid of spaces left over between parameters.
        if check_same == original_command:  # Check if we are stuck in a loop due to formatting errors.
            print("Error, Something went wrong. Likely formatted incorrectly.")
            return None
        print(command_list)
        print(original_command)
        sleep(1)


class LanguageBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.languages = []
        self.prefix = '\\'  # What should be in front of commands. This also allows the users to change it to prevent conflict with other bots.
        self.run_task = self.loop.create_task(self.background_tasks())

    async def background_tasks(self):
        await self.wait_until_ready()
        pass

    async def on_message(self, message):
        print("Received Message")
        if message.content[:len(self.prefix)] == self.prefix:  # If the beginning of the message has the proper prefix.
            total_command = message.content[len(self.prefix):]
            command_list = get_command_list(total_command)



bot = LanguageBot()
bot.run("")