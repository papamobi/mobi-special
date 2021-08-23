#!/usr/bin/env python3
import configparser
import discord
import os

BOT_TOKEN = os.environ["BOT_TOKEN"]
CONFIG_CHANNEL_PREFIX = "channel:"
NUMBER_EMOJIS = (
    u'\U00000031\U0000FE0F\U000020E3',  # one
    u'\U00000032\U0000FE0F\U000020E3',
    u'\U00000033\U0000FE0F\U000020E3',
    u'\U00000034\U0000FE0F\U000020E3',
    u'\U00000035\U0000FE0F\U000020E3',
    u'\U00000036\U0000FE0F\U000020E3',
    u'\U00000037\U0000FE0F\U000020E3',
    u'\U00000038\U0000FE0F\U000020E3',
    u'\U00000039\U0000FE0F\U000020E3',
)

config = configparser.ConfigParser()
config.read("config.ini")

client = discord.Client()
channel_ids_to_watch = list(map(
    lambda section: int(section[len(CONFIG_CHANNEL_PREFIX):]),
    filter(
        lambda section: section.startswith(CONFIG_CHANNEL_PREFIX),
        config.sections()
    )
))
ongoing_votes = {}


class Callvote:
    def __init__(self, channel, user_ids, servers):
        self.channel = channel
        self.message = None
        self.user_ids = user_ids
        self.servers = servers
        self.votes = {user_id: set() for user_id in user_ids}

    def get_server_index_from_reaction(self, user, emoji):
        try:
            server_index = NUMBER_EMOJIS.index(emoji)
        except ValueError:
            return

        if not (server_index < len(self.servers)):
            return

        if user.id not in self.user_ids:
            return

        return server_index

    def vote(self, user, emoji):
        server_index = self.get_server_index_from_reaction(user, emoji)
        if server_index is not None:
            self.votes[user.id] = server_index
            return True
        return False

    def get_server_vote_count(self, server_index):
        return len([True for x in self.votes.items() if server_index == x[1]])

    def prepare_message(self):
        server_vote_counts = [self.get_server_vote_count(x) for x, _ in enumerate(self.servers)]

        return """
```
Vote for server!
{}
```
        """.format("\n".join(map(
            lambda x: "{}. {} ({})".format(x[0], x[1], server_vote_counts[x[0]]),
            enumerate(self.servers)
        )))

    async def update_message(self):
        if self.message is None:
            self.message = await self.channel.send(self.prepare_message())
            for emoji, _ in zip(NUMBER_EMOJIS, self.servers):
                await self.message.add_reaction(emoji)
        else:
            await self.message.edit(content=self.prepare_message())


def read_channel_config(channel_id, key):
    try:
        return config["{}{}".format(CONFIG_CHANNEL_PREFIX, channel_id)][key]
    except KeyError:
        return config["defaults"][key]


def get_fav_servers_by_channel_id(channel_id):
    return list(map(
        lambda s: s.strip(),
        read_channel_config(channel_id, "servers").split(",")
    ))


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))


@client.event
async def on_reaction_add(reaction, user):
    vote = ongoing_votes.get(reaction.message.channel.id)
    if not vote:
        return

    if vote.message != reaction.message:
        return

    if vote.vote(user, reaction.emoji):
        await vote.update_message()
        await reaction.remove(user)


@client.event
async def on_message(message: discord.message.Message):
    if message.author == client.user:
        return

    if message.channel.id not in channel_ids_to_watch:
        return

    servers = get_fav_servers_by_channel_id(message.channel.id)

    ongoing_votes[message.channel.id] = Callvote(message.channel, [137993947032059904, 232898482774605824], servers)
    await ongoing_votes[message.channel.id].update_message()


client.run(BOT_TOKEN)
# TODO: timeout 50 секунд. После таймаута - новое сообщение куда коннектитться
# TODO: parse user_ids from new pubbbot message
# message.embeds[0].to_dict()['fields'][0]['value']
# '\u200b <@137993947032059904>\n \u200b <@232898482774605824>'
# message.embeds[0].to_dict()['fields'][0]['name']
# 'Players'
# message.embeds[0].fields[0].value
# message.embeds[0].title
# '__**1v1** has started!__'
# TODO: нумерация с 1, а не с нуля
