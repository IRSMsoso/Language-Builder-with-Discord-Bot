# I'm going to use the discord.py module for creating a discord bot. https://github.com/Rapptz/discord.py
# Asyncio is required to interact with the discord bot. asyncio.sleep() is useful as well. After these are included, it's easier to write the entire program asynchronously.
# Pickle is used for saving languages to binary file.
import discord
import asyncio
import pickle
import time
from enum import Enum
from enum import auto
import os.path


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
        self.time_remaining = 20.0  # 172,800.0
        self.voting_message = None

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

class Language:

    def __init__(self, name="New Language"):
        self.punctuations = []
        self.words = []
        self.name = name
        self.channel_id = None
        self.rules = []
        self.intro_message = None
        self.amendments = []
        self.should_update_rules = False

    async def get_word(self, text):
        for word in self.words:
            if word.text == text:
                return word

        return None


def get_command_list(full_command):
    original_command = full_command
    first_command_index = original_command.find('\"')
    if first_command_index == -1:  # There's a problem if there is no quotes in the command.
        # print("Error, Something went wrong. Likely formatted incorrectly.")
        return None
    command_list = [original_command[:first_command_index]]  # Create a list of commands starting with the base command.
    command_list[0] = command_list[0].replace(' ',
                                              '')  # Replace any spaces since the first command can never have them.
    original_command = original_command[first_command_index:]  # Remove that first command from the rest of the string.
    # print("Command List:")
    # print(command_list)
    # print("Original Command")
    # print(original_command)
    while len(original_command) > 0:  # Until everything is drained form the string of commands.
        check_same = original_command
        command_list.append(original_command[1:original_command.find('\"', 1)])
        original_command = original_command[original_command.find('\"', 1) + 1:]
        original_command = original_command[
                           original_command.find('\"'):]  # Get rid of spaces left over between parameters.
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
        self.prefix = '\\'  # What should be in front of commands. This also allows the users to *eventually* change it to prevent conflict with other bots.
        self.run_task = self.loop.create_task(self.background_tasks())
        if os.path.isfile("languages.cam"):
            self.load_languages()
        print("Done init")

    async def save_languages(self):
        file = open("languages.cam", 'wb')
        pickle.dump(self.languages, file)
        file.close()
        print("Saved File")

    async def load_languages(self):
        file = open("languages.cam", 'rb')
        self.languages = pickle.load(file)
        file.close()
        print("Loaded File")

    async def make_change(self, change, language):
        change_type = change.change_type

        if change_type == ChangeType.ADDWORD:
            new_word = Word(change.text, change.pronunciation, change.definition, related_words=change.related_words)
            language.words.append(new_word)
            print("Added Word")

        elif change_type == ChangeType.EDITWORD:
            word = language.get_word(change.text)
            if word is not None:
                if change.parameter == "text":
                    word.text = change.modification
                elif change.parameter == "pronunciation":
                    word.pronunciation = change.modification
                elif change.parameter == "definition":
                    word.definition = change.modification

                print("Modified Word")

        elif change_type == ChangeType.REMOVEWORD:
            word = language.get_word(change.text)
            if word is not None:
                language.words.remove(word)
                print("Removed Word")

        elif change_type == ChangeType.ADDRULE:
            language.rules.append(change.rule_desc)
            language.should_update_rules = True
            print("Added Rule")

        elif change_type == ChangeType.EDITRULE:
            if change.rule_number in range(1, len(language.rules)):
                language.rules[change.rule_number - 1] = change.rule_desc
                language.should_update_rules = True
                print("Updated Rule")

        elif change_type == ChangeType.REMOVERULE:
            if change.rule_number in range(1, len(language.rules)):
                del language.rules[change.rule_number - 1]
                language.should_update_rules = True
                print("Deleted Rule")

        elif change_type == ChangeType.CHANGENAME:
            language.name = change.new_name
            language.should_update_rules = True
            print("Changed Language Name")

        elif change_type == ChangeType.ADDRELATEDWORD:
            word = language.get_word(change.text)
            related_word = language.get_word(change.related_word_text)
            if (word is not None) and (related_word is not None):
                word.related_words.append(related_word)
                print("Added related word")

        elif change_type == ChangeType.REMOVERELATEDWORD:
            word = language.get_word(change.text)
            related_word = language.get_word(change.related_word_text)
            if (word is not None) and (related_word is not None):
                word.related_words.remove(related_word)
                print("Removed related word")

    async def background_tasks(self):
        print("Started Task")
        await self.wait_until_ready()
        print("ready")

        previous_time = time.time()
        while self.is_ready():
            # Get and reset the time.
            time_difference = time.time() - previous_time
            previous_time = time.time()

            for language in self.languages:

                for amendment in language.amendments:
                    amendment.time_remaining -= time_difference
                    if amendment.time_remaining <= 0:
                        yes_votes = 0
                        no_votes = 0
                        # Get Both Reactions
                        for reaction in amendment.voting_message.reactions:
                            if reaction.emoji == ":white_check_mark:":
                                yes_votes = reaction.count - 1  # -1 Due to one made by the bot.

                            if reaction.emoji == ":x:":
                                no_votes = reaction.count - 1

                        if yes_votes > no_votes:
                            await self.make_change(amendment, language)
                            language.amendments.remove(amendment)
                            await self.save_languages()
                            print("Made Change")

                if language.should_update_rules:
                    new_message = "Language: " + language.name + "\nRules:\n"
                    for index, rule in enumerate(language.rules):
                        new_message += str(index + 1) + ": " + rule
                    await language.intro_message.edit(new_message)
                    language.should_update_rules = False

            await asyncio.sleep(5)

    async def get_language_from_channel(self, channel_id):
        for language in self.languages:
            if language.channel_id == channel_id:
                return language
        return None

    async def on_message(self, message):
        print("Received Message")
        if message.content[:len(self.prefix)] == self.prefix:  # If the beginning of the message has the proper prefix.

            # PARSE THE COMMAND
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

                    # Send and remember two messages for rules and amendments.
                    new_language.intro_message = await message.channel.send("Language: " + new_language.name + "\nRules:\n")

                    # Pin those messages.
                    await new_language.intro_message.pin()

                    self.languages.append(new_language)
                    await self.save_languages()
                    print("Created new language: " + new_language.name)
                else:
                    print("Could not create language. Channel already has one.")
            elif main_command == "dictionary":  # Send user a text file dictionary of the language.
                pass
            else:
                correct_message = True
                new_change = Change()
                voting_message = None
                if main_command == "addrule" and len(command_list) == 2:
                    new_change.change_type = ChangeType.ADDRULE
                    new_change.rule_desc = command_list[1]

                    voting_message = "Change:\nAdd Rule: " + command_list[1]

                elif main_command == "editrule" and len(command_list) == 3:
                    new_change.change_type = ChangeType.EDITRULE
                    try:
                        rule_number = int(command_list[1])
                    except:
                        print("Error converting integer.")
                        return
                    new_change.rule_number = rule_number
                    new_change.rule_desc = command_list[2]

                    voting_message = "Change:\nChange rule " + str(rule_number) + " to " + '"' + command_list[2] + '"'

                elif main_command == "removerule" and len(command_list) == 2:
                    new_change.change_type = ChangeType.REMOVERULE
                    try:
                        rule_number = int(command_list[1])
                    except:
                        print("Error converting integer.")
                        return
                    new_change.rule_number = rule_number

                    voting_message = "Change:\nRemove Rule " + str(rule_number)

                elif main_command == "changename" and len(command_list) == 2:
                    new_change.change_type = ChangeType.CHANGENAME
                    new_change.new_name = command_list[1]

                    voting_message = 'Change:\nChange language name to "' + command_list[1]

                elif main_command == "addword" and len(command_list) >= 4:
                    new_change.change_type = ChangeType.ADDWORD
                    new_change.text = command_list[1]
                    new_change.pronunciation = command_list[2]
                    new_change.definition = command_list[3]
                    related_words = []
                    if len(main_command) > 4:
                        for i in range(4, len(main_command)):
                            related_words.append(command_list[i])
                        new_change.related_words = related_words

                    voting_message = "Change: Add Word\nText: " + command_list[1] + "\nPronunciation: " + command_list[2] + "\nDefinition: " + command_list[3] + "\nRelated Words: "
                    for word in related_words:
                        voting_message += word + ", "


                elif main_command == "removeword" and len(command_list) == 2:
                    new_change.change_type = ChangeType.REMOVEWORD
                    new_change.text = command_list[1]

                    voting_message = "Change:\nRemove Word: " + command_list[1]

                elif main_command == "editword" and len(command_list) == 4:
                    new_change.change_type = ChangeType.EDITWORD
                    new_change.text = command_list[1]
                    new_change.parameter = command_list[2].lower()
                    new_change.modification = command_list[3]

                    voting_message = "Change:\nChange \"" + command_list[1] + "\"'s " + command_list[2].lower() + " to " + command_list[3]

                elif main_command == "addrelatedword" and len(command_list) == 3:
                    new_change.change_type = ChangeType.ADDRELATEDWORD
                    new_change.text = command_list[1]
                    new_change.related_word_text = command_list[2]

                    voting_message = "Change:\nAdd \"" + command_list[2] + "\" as a related word to \"" + command_list[1] + '"'

                elif main_command == "removerelatedword" and len(command_list) == 3:
                    new_change.change_type = ChangeType.REMOVERELATEDWORD
                    new_change.text = command_list[1]
                    new_change.related_word_text = command_list[2]

                    voting_message = "Change:\nRemove \"" + command_list[2] + "\" as a related word to \"" + command_list[1] + '"'

                else:
                    print("Incorrect Message")
                    correct_message = False

                if correct_message:
                    language = await self.get_language_from_channel(message.channel.id)
                    if language is not None:
                        new_change.voting_message = await message.channel.send(voting_message)
                        print(await new_change.voting_message.add_reaction(":white_check_mark:"))
                        await new_change.voting_message.add_reaction(":x:")
                        language.amendments.append(new_change)
                        await self.save_languages()
                        print("Amendments: " + str(language.amendments))
                    else:
                        print("Error, no language in channel.")


bot = LanguageBot()
bot.run("")
