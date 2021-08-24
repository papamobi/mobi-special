#!/usr/bin/env python3
import asyncio
import configparser
import discord
import logging
import os
import random
import re
from time import time

_logger = logging.getLogger(__name__)

VOTE_TIME = 50
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
        self.is_finished = False
        self.finish_time = time() + VOTE_TIME

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

    def can_be_finished_now(self):
        if self.finish_time < time():
            return True

        for i, server in enumerate(self.servers):
            if self.get_server_vote_count(i) > len(self.servers) / 2:
                return True
        return False

    async def finish(self):
        max_votes = 0
        max_voted_servers = []
        for i, server in enumerate(self.servers):
            if self.get_server_vote_count(i) > max_votes:
                max_votes = self.get_server_vote_count(i)
                max_voted_servers = [server]
            elif self.get_server_vote_count(i) == max_votes:
                max_voted_servers.append(server)

        self.is_finished = True
        chosen_server = random.choice(max_voted_servers)
        await self.message.channel.send("""
```
Vote finished.
Join to server: /connect {}
```
        """.format(chosen_server))

    def prepare_message(self):
        server_vote_counts = [self.get_server_vote_count(x) for x, _ in enumerate(self.servers)]

        return """
```
Choose a server!
{server_list}
Time left to vote: {vote_seconds_left} s.
```
        """.format(
            server_list="\n".join(map(
                lambda x: "{}. {} ({})".format(x[0] + 1, x[1], server_vote_counts[x[0]]),
                enumerate(self.servers)
            )),
            vote_seconds_left=int(self.finish_time - time()),
        )

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

    pickup_bot_id = int(read_channel_config(message.channel.id, "pickup_bot_id"))
    if message.author.id != pickup_bot_id:
        return

    if message.content != '':
        return

    player_ids = []
    for embed in message.embeds:
        if "has started" not in embed.title:
            continue

        for field in embed.fields:
            if field.name == 'Players':
                player_ids = list(map(int, re.findall(r"<@([0-9]+)>", field.value)))
                break

    servers = get_fav_servers_by_channel_id(message.channel.id)

    if not servers or not player_ids:
        return

    ongoing_votes[message.channel.id] = Callvote(message.channel, player_ids, servers)
    await ongoing_votes[message.channel.id].update_message()

    while(True):
        await ongoing_votes[message.channel.id].update_message()
        await asyncio.sleep(1)
        if ongoing_votes[message.channel.id].can_be_finished_now():
            await ongoing_votes[message.channel.id].finish()
            break


client.run(BOT_TOKEN)
