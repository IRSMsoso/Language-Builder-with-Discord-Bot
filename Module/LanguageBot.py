# I'm going to use the discord.py module for creating a discord bot. https://github.com/Rapptz/discord.py
# Asyncio is required to interact with the discord bot. asyncio.sleep() is useful as well.
# After these are included, it's easier to just write the entire program asynchronously.
# Pickle is used for saving languages to binary file.
import discord
import asyncio
import pickle
import time
from enum import Enum
from enum import auto
import os.path


# Enum to classify all the different types of amendments that can occur.
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
        self.time_remaining = 60.0  # 172,800.0 normally. Lower for testing.
        self.voting_message_id = None

    def __str__(self):
        return str(self.change_type)


class Word:
    """
    Word

    Really just a storage class for all the information
    that makes up a word.
    """

    def __init__(self, text, pronunciation, definition, related_words=None):
        self.text = text
        self.pronunciation = pronunciation
        self.definition = definition
        if related_words is None:  # None is needed because of this: https://stackoverflow.com/questions/41686829/warning-about-mutable-default-argument-in-pycharm
            self.related_words = []
        else:
            self.related_words = related_words


class Language:
    """
    Language

    Handles the data that makes up each language
    as well as some searching and serialization helper methods.
    """

    def __init__(self, name="New Language"):
        self.words = []
        self.name = name
        self.channel_id = None
        self.rules = []
        self.intro_message_id = None
        self.amendments = []
        self.should_update_rules = False

    async def get_word(self, text):
        """

        :param text: The text of the word to get from this language.
        :return: The gotten word, or None if it wasn't found.
        """

        for word in self.words:
            if word.text == text:
                return word

        return None

    async def get_pickle_data(self):
        """
        Gets data from the language for pickling.
        :return: The data.
        """

        return [self.name, self.words, self.channel_id, self.rules, self.intro_message_id, self.amendments]

    async def build_from_pickle_data(self, data):
        """
        Rebuilds the data from pickled data when loading.
        :param data: The data to unpack.
        :return: Nothing.
        """

        self.name = data[0]
        self.words = data[1]
        self.channel_id = data[2]
        self.rules = data[3]
        self.intro_message_id = data[4]
        self.amendments = data[5]


def get_command_list(full_command):
    """
    Helper function that *painfully* parses the string given to a usable format.
    :param full_command: The raw command minus the prefix.
    :return: Ideally a list of commands and parameters. None if there was an error.
    """

    original_command = full_command
    first_command_index = original_command.find('\"')
    if first_command_index == -1:
        return [full_command]
    command_list = [original_command[:first_command_index]]  # Create a list of commands starting with the base command.
    command_list[0] = command_list[0].replace(' ',
                                              '')  # Replace any spaces since the first command can never have them.
    original_command = original_command[first_command_index:]  # Remove that first command from the rest of the string.
    while len(original_command) > 0:  # Until everything is drained form the string of commands.
        check_same = original_command
        command_list.append(original_command[1:original_command.find('\"', 1)])
        original_command = original_command[original_command.find('\"', 1) + 1:]
        original_command = original_command[
                           original_command.find('\"'):]  # Get rid of spaces left over between parameters.
        if check_same == original_command:  # Check if we are stuck in a loop due to formatting errors.
            return None
        # sleep(1)
    return command_list


async def make_change(change, language):
    """
    Modifies the language in accordance to the change presented.
    This is what is called when the changes are ready to be put into place from voting.
    :param change: The change that is about to happen, including all the data needed to know what to do.
    :param language: The language to modify.
    :return: Nothing
    """

    change_type = change.change_type

    if change_type == ChangeType.ADDWORD:
        new_word = Word(change.text, change.pronunciation, change.definition, related_words=change.related_words)
        language.words.append(new_word)

    elif change_type == ChangeType.EDITWORD:
        word = await language.get_word(change.text)
        if word is not None:
            if change.parameter == "text":
                word.text = change.modification
            elif change.parameter == "pronunciation":
                word.pronunciation = change.modification
            elif change.parameter == "definition":
                word.definition = change.modification

    elif change_type == ChangeType.REMOVEWORD:
        word = await language.get_word(change.text)
        if word is not None:
            language.words.remove(word)

    elif change_type == ChangeType.ADDRULE:
        language.rules.append(change.rule_desc)
        language.should_update_rules = True

    elif change_type == ChangeType.EDITRULE:
        if 1 <= change.rule_number <= len(language.rules):
            language.rules[change.rule_number - 1] = change.rule_desc
            language.should_update_rules = True

    elif change_type == ChangeType.REMOVERULE:
        if 1 <= change.rule_number <= len(language.rules):
            del language.rules[change.rule_number - 1]
            language.should_update_rules = True

    elif change_type == ChangeType.CHANGENAME:
        language.name = change.new_name
        language.should_update_rules = True

    elif change_type == ChangeType.ADDRELATEDWORD:
        word = await language.get_word(change.text)
        related_word = await language.get_word(change.related_word_text)
        if (word is not None) and (related_word is not None):
            word.related_words.append(related_word)

    elif change_type == ChangeType.REMOVERELATEDWORD:
        word = await language.get_word(change.text)
        related_word = await language.get_word(change.related_word_text)
        if (word is not None) and (related_word is not None):
            word.related_words.remove(related_word)


class LanguageBot(discord.Client):
    """
    The meat of the program. Handles the discord bot, as well as
    the background processes for handling the voting system.
    Also has all of the languages instanced inside it.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.languages = []
        self.prefix = '\\'  # What should be in front of commands. This also allows the users to *eventually* change it to prevent conflict with other bots.
        self.run_task = self.loop.create_task(self.background_tasks())
        if os.path.isfile("languages.cam"):
            asyncio.get_event_loop().run_until_complete(self.load_languages())

    async def save_languages(self):
        """
        Save all the languages to file so they are not lost.
        :return: nothing.
        """

        file = open("languages.cam", 'wb')
        data = []
        for language in self.languages:
            data.append(await language.get_pickle_data())
        pickle.dump(data, file)
        file.close()
        print("Saved File")

    async def load_languages(self):
        """
        Load all the languages into memory from a file.
        :return: nothing.
        """

        file = open("languages.cam", 'rb')
        data = pickle.load(file)
        for language_data in data:
            new_language = Language()
            await new_language.build_from_pickle_data(language_data)
            self.languages.append(new_language)
        file.close()
        print("Loaded File")

    async def background_tasks(self):
        """
        This method is initiated from the bot's constructor, and waits until
        the bot is logged in and ready. This is essentially all the stuff that
        needs to be done over and over constantly. (Voting, updating messages, etc.)
        :return: nothing.
        """

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
                    message = await self.get_channel(language.channel_id).fetch_message(amendment.voting_message_id)

                    current_message_content = message.content
                    current_message_content = current_message_content.replace(current_message_content[:current_message_content.find("\n")], "Time Remaining: " + str(round(amendment.time_remaining)))

                    await message.edit(content=current_message_content)

                    if amendment.time_remaining <= 0:
                        yes_votes = 0
                        no_votes = 0
                        # Get Both Reactions

                        for reaction in message.reactions:
                            if reaction.emoji == "✅":
                                yes_votes = reaction.count - 1  # -1 Due to one made by the bot.

                            if reaction.emoji == "❌":
                                no_votes = reaction.count - 1

                        if yes_votes > no_votes:
                            await make_change(amendment, language)
                            language.amendments.remove(amendment)
                            await self.save_languages()
                            print("Made Change")
                        else:
                            language.amendments.remove(amendment)
                            await self.save_languages()
                            print("Rejected Change")

                        await message.delete()

                if language.should_update_rules:
                    new_message = "Language: " + language.name + "\nRules:\n"
                    for index, rule in enumerate(language.rules):
                        new_message += str(index + 1) + ": " + rule + "\n"
                    message = await self.get_channel(language.channel_id).fetch_message(language.intro_message_id)
                    await message.edit(content=new_message)
                    language.should_update_rules = False

            await asyncio.sleep(5)

    async def get_language_from_channel(self, channel_id):
        """
        Helper function that returns the language associated with a particular discord channel.
        :param channel_id: id of the discord channel.
        :return: The language associated.
        """

        for language in self.languages:
            if language.channel_id == channel_id:
                return language
        return None

    async def on_message(self, message):
        """
        This is a overwritten method from the Client base class. It is called
        each time the bot sees someone send a message, which makes it perfect
        for looking for commands.
        :param message: The message sent. (discord.Message)
        :return: nothing.
        """

        if (message.content[:len(self.prefix)] == self.prefix) and (message.author.id != self.user.id):  # If the beginning of the message has the proper prefix.

            # PARSE THE COMMAND using functions and methods above.
            total_command = message.content[len(self.prefix):]
            command_list = get_command_list(total_command)
            if command_list is None:
                print("Error. Bad Commands.")
                return

            # EXECUTE THE COMMAND
            main_command = command_list[0]
            if main_command == "createlanguage" and len(command_list) == 2:  # Create a Language.
                if await self.get_language_from_channel(message.channel.id) is None:
                    new_language = Language(name=command_list[1])
                    new_language.channel_id = message.channel.id

                    # Send and remember two messages for rules and amendments.
                    intro_message = await message.channel.send("Language: " + new_language.name + "\nRules:\n")
                    new_language.intro_message_id = intro_message.id

                    # Pin those messages.
                    # await intro_message.pin()

                    self.languages.append(new_language)
                    await self.save_languages()
                    print("Created new language: " + new_language.name)
                else:
                    print("Could not create language. Channel already has one.")
            elif main_command == "dictionary":  # Send user a text file dictionary of the language.
                language = await self.get_language_from_channel(message.channel.id)
                if language is not None:
                    file = open("dictionary.txt", 'w')
                    file.write(language.name + "\nRules:\n")
                    for index, rule in enumerate(language.rules):
                        file.write(str(index + 1) + ": " + rule + "\n")
                    file.write("--------------------------\nWords:\n")
                    for word in language.words:
                        file.write(word.text + "\nPronunciation: " + word.pronunciation + "\nDefinition: " + word.definition + "\nRelated Words: ")

                        for related_word in word.related_words:
                            file.write(related_word.text + ", ")
                        file.write("\n\n")

                    file.close()

                    discord_file = discord.File(open("dictionary.txt", 'rb'))
                    dm = await message.author.create_dm()
                    await dm.send(file=discord_file)

            else:  # Everything else can be treated as submitting something as an ammendment.
                correct_message = True
                new_change = Change()
                voting_message_string = None
                if main_command == "addrule" and len(command_list) == 2:
                    new_change.change_type = ChangeType.ADDRULE
                    new_change.rule_desc = command_list[1]

                    voting_message_string = "Time Remaining: " + str(new_change.time_remaining) + "\nChange:\nAdd Rule: " + command_list[1]

                elif main_command == "editrule" and len(command_list) == 3:
                    new_change.change_type = ChangeType.EDITRULE
                    try:
                        rule_number = int(command_list[1])
                    except:
                        print("Error converting integer.")
                        return
                    new_change.rule_number = rule_number
                    new_change.rule_desc = command_list[2]

                    voting_message_string = "Time Remaining: " + str(new_change.time_remaining) + "\nChange:\nChange rule " + str(rule_number) + " to " + '"' + command_list[2] + '"'

                elif main_command == "removerule" and len(command_list) == 2:
                    new_change.change_type = ChangeType.REMOVERULE
                    try:
                        rule_number = int(command_list[1])
                    except:
                        print("Error converting integer.")
                        return
                    new_change.rule_number = rule_number
                    voting_message_string = "Time Remaining: " + str(new_change.time_remaining) + "\nChange:\nRemove Rule " + str(rule_number)

                elif main_command == "changename" and len(command_list) == 2:
                    new_change.change_type = ChangeType.CHANGENAME
                    new_change.new_name = command_list[1]

                    voting_message_string = "Time Remaining: " + str(new_change.time_remaining) + '\nChange:\nChange language name to "' + command_list[1] + '"'

                elif main_command == "addword" and len(command_list) >= 4:
                    new_change.change_type = ChangeType.ADDWORD
                    new_change.text = command_list[1]
                    new_change.pronunciation = command_list[2]
                    new_change.definition = command_list[3]
                    related_words = []
                    if len(command_list) > 4:
                        for i in range(4, len(command_list)):
                            related_words.append(command_list[i])
                    new_change.related_words = related_words

                    voting_message_string = "Time Remaining: " + str(new_change.time_remaining) + "\nChange: Add Word\nText: " + command_list[1] + "\nPronunciation: " + command_list[2] + "\nDefinition: " + command_list[3] + "\nRelated Words: "
                    for word in related_words:
                        voting_message_string += word + ", "

                elif main_command == "removeword" and len(command_list) == 2:
                    new_change.change_type = ChangeType.REMOVEWORD
                    new_change.text = command_list[1]

                    voting_message_string = "Time Remaining: " + str(new_change.time_remaining) + "\nChange:\nRemove Word: " + command_list[1]

                elif main_command == "editword" and len(command_list) == 4:
                    new_change.change_type = ChangeType.EDITWORD
                    new_change.text = command_list[1]
                    new_change.parameter = command_list[2].lower()
                    new_change.modification = command_list[3]

                    voting_message_string = "Time Remaining: " + str(new_change.time_remaining) + "\nChange:\nChange \"" + command_list[1] + "\"'s " + command_list[2].lower() + " to " + command_list[3]

                elif main_command == "addrelatedword" and len(command_list) == 3:
                    new_change.change_type = ChangeType.ADDRELATEDWORD
                    new_change.text = command_list[1]
                    new_change.related_word_text = command_list[2]

                    voting_message_string = "Time Remaining: " + str(new_change.time_remaining) + "\nChange:\nAdd \"" + command_list[2] + "\" as a related word to \"" + command_list[1] + '"'

                elif main_command == "removerelatedword" and len(command_list) == 3:
                    new_change.change_type = ChangeType.REMOVERELATEDWORD
                    new_change.text = command_list[1]
                    new_change.related_word_text = command_list[2]

                    voting_message_string = "Time Remaining: " + str(new_change.time_remaining) + "\nChange:\nRemove \"" + command_list[2] + "\" as a related word to \"" + command_list[1] + '"'

                else:  # If none of these commands were triggered, something went wrong.
                    print("Incorrect Message")
                    correct_message = False

                if correct_message:
                    language = await self.get_language_from_channel(message.channel.id)
                    if language is not None:  # Common logic for all of the amendments.
                        voting_message = await message.channel.send(voting_message_string)
                        new_change.voting_message_id = voting_message.id
                        await voting_message.add_reaction("✅")
                        await voting_message.add_reaction("❌")
                        language.amendments.append(new_change)
                        await self.save_languages()  # Save when important stuff happens.
                    else:
                        print("Error, no language in channel.")  # Command was invoked in a language-less channel.

            await message.delete()  # Get rid of all the junk (not the bot's messages though)


bot = LanguageBot()
bot.run("")
