# I'm going to use the discord.py module for creating a discord bot. https://github.com/Rapptz/discord.py
# Asyncio is required to interact with the discord bot. asyncio.sleep() is useful as well. After these are included, it's easier to write the entire program asynchronously.
# Pickle is used for saving languages to binary file.
import discord
import asyncio
import pickle
from time import sleep
from enum import Enum
from enum import auto


class ChangeType(Enum):
    ADDRULE = auto()
    EDITRULE = auto()
    REMOVERULE = auto()
    CHANGENAME = auto()
    ADDWORD = auto()
    REMOVEWORD = auto()
    EDITWORD = auto()
    ADDRELATEDWORD = auto()
    REMOVERELATEDWORD = auto()


class Change:

    def __init__(self, change_type=None):
        self.change_type = change_type
        self.time_remaining = 20  # 172,800

    def __str__(self):
        return str(self.change_type)


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


class Language:

    def __init__(self, name="New Language"):
        self.punctuations = []
        self.words = []
        self.name = name
        self.channel_id = None
        self.rules = []
        self.intro_message = None
        self.voting_message = None
        self.amendments = []


def get_command_list(full_command):
    original_command = full_command
    first_command_index = original_command.find('\"')
    if first_command_index == -1:  # There's a problem if there is no quotes in the command.
        # print("Error, Something went wrong. Likely formatted incorrectly.")
        return None
    command_list = [original_command[:first_command_index]]  # Create a list of commands starting with the base command.
    command_list[0] = command_list[0].replace(' ', '')  # Replace any spaces since the first command can never have them.
    original_command = original_command[first_command_index:]  # Remove that first command from the rest of the string.
    # print("Command List:")
    # print(command_list)
    # print("Original Command")
    # print(original_command)
    while len(original_command) > 0:  # Until everything is drained form the string of commands.
        check_same = original_command
        command_list.append(original_command[1:original_command.find('\"', 1)])
        original_command = original_command[original_command.find('\"', 1) + 1:]
        original_command = original_command[original_command.find('\"'):]  # Get rid of spaces left over between parameters.
        if check_same == original_command:  # Check if we are stuck in a loop due to formatting errors.
            # print("Error, Something went wrong. Likely formatted incorrectly.")
            return None
        # print(command_list)
        # print(original_command)
        # sleep(1)
    return command_list



class LanguageBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.languages = []
        self.prefix = '\\'  # What should be in front of commands. This also allows the users to change it to prevent conflict with other bots.
        self.run_task = self.loop.create_task(self.background_tasks())

    async def background_tasks(self):
        await self.wait_until_ready()

    async def get_language_from_channel(self, channel_id):
        for language in self.languages:
            if language.channel_id == channel_id:
                return language
        return None

    async def on_message(self, message):
        print("Received Message")
        if message.content[:len(self.prefix)] == self.prefix:  # If the beginning of the message has the proper prefix.
            total_command = message.content[len(self.prefix):]
            command_list = get_command_list(total_command)
            if command_list is None:
                print("Error. Bad Commands.")
                return
            print("Command List: " + str(command_list))

            # EXECUTE THE COMMAND

            main_command = command_list[0]
            if main_command == "createlanguage" and len(command_list) == 2:
                if await self.get_language_from_channel(message.channel.id) is None:
                    new_language = Language(name=command_list[1])
                    new_language.channel_id = message.channel.id

                    # Send and remember two messages for rules and ammendments.
                    new_language.intro_message = await message.channel.send("Language: " + new_language.name + "\nRules:\n")
                    new_language.voting_message = await message.channel.send("Amendments:\n")

                    # Pin those messages.
                    await new_language.intro_message.pin()
                    await new_language.voting_message.pin()

                    self.languages.append(new_language)
                    print("Created new language: " + new_language.name)
                else:
                    print("Could not create language. Channel already has one.")
            elif main_command == "dictionary":
                pass
            else:
                correct_message = True
                new_change = Change()
                if main_command == "addrule" and len(command_list) == 2:
                    new_change.change_type = ChangeType.ADDRULE
                    new_change.rule_desc = command_list[1]

                elif main_command == "editrule" and len(command_list) == 3:
                    new_change.change_type = ChangeType.EDITRULE
                    try:
                        rule_number = int(command_list[1])
                    except:
                        print("Error converting integer.")
                        return
                    new_change.rule_number = rule_number
                    new_change.rule_desc = command_list[2]
                elif main_command == "removerule" and len(command_list) == 2:
                    new_change.change_type = ChangeType.REMOVERULE
                    try:
                        rule_number = int(command_list[1])
                    except:
                        print("Error converting integer.")
                        return
                    new_change.rule_number = rule_number
                elif main_command == "changename" and len(command_list) == 2:
                    new_change.change_type = ChangeType.CHANGENAME
                    new_change.new_name = command_list[1]
                elif main_command == "addword" and len(command_list) >= 4:
                    new_change.change_type = ChangeType.ADDWORD
                    new_change.text = command_list[1]
                    new_change.pronunciation = command_list[2]
                    new_change.definition = command_list[3]
                    if len(main_command) > 4:
                        related_words = []
                        for i in range(4, len(main_command)):
                            related_words.append(command_list[i])
                        new_change.related_words = related_words
                elif main_command == "removeword" and len(command_list) == 2:
                    new_change.change_type = ChangeType.REMOVEWORD
                    new_change.text = command_list[1]
                elif main_command == "editword" and len(command_list) == 4:
                    new_change.change_type = ChangeType.EDITWORD
                    new_change.text = command_list[1]
                    new_change.parameter = command_list[2].lower()
                    new_change.modification = command_list[3]
                elif main_command == "addrelatedword" and len(command_list) == 3:
                    new_change.change_type = ChangeType.ADDRELATEDWORD
                    new_change.text = command_list[1]
                    new_change.related_word_text = command_list[2]
                elif main_command == "removerelatedword" and len(command_list) == 3:
                    new_change.change_type = ChangeType.REMOVERELATEDWORD
                    new_change.text = command_list[1]
                    new_change.related_word_text = command_list[2]
                else:
                    print("Incorrect Message")
                    correct_message = False

                if correct_message:
                    language = await self.get_language_from_channel(message.channel.id)
                    if language is not None:
                        language.amendments.append(new_change)
                        print("Amendments: " + str(language.amendments))
                    else:
                        print("Error, no language in channel.")







bot = LanguageBot()
bot.run("")