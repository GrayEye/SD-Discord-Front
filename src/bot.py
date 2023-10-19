import discord
import os
import random
from dotenv import load_dotenv

load_dotenv()

client = discord.Client()
token = os.getenv('TOKEN')




@client.event
async def on_ready():
    print("Logged in as a bot {0.user}".format(client))


@client.event
async def on_message(message):
    username = str(message.author).split("#")[0]
    channel = str(message.channel.name)
    user_message = str(message.content)

    print(f'Message {user_message} by {username} on {channel}')

    if message.author == client.user:
        return

    if channel == "random":
        if user_message.lower() == "hello" or user_message.lower() == "hi":
            await message.channel.send(f'Hello {username}')
            return
        elif user_message.lower() == "bye":
            await message.channel.send(f'Bye {username}')
        elif user_message.lower() == "tell me a joke":
            jokes = [" Can someone please shed more\
                     light on how my lamp got stolen?",
                     "Why is she called llene? She\
            stands on equal legs.",
                     "What do you call a gazelle in a \
            lions territory? Denzel."]
            await message.channel.send(random.choice(jokes))



client.run(token)