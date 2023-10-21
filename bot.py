import base64
import discord
import hashlib
import io
import json
import os
import requests
from discord import Intents
from discord.ext import commands
from dotenv import load_dotenv
from PIL import Image

load_dotenv()
token = os.getenv('TOKEN')
url = os.getenv('URL')

intents = Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.command()
async def prompt(ctx, *args):
    imageName = get_image(build_payload(' '. join(args)), url)
    await ctx.send(file=discord.File(imageName))

def build_payload(input):
    payload = {
        "prompt": input,
        "steps": 20
    }
    return payload

def get_image(payload, url):
    response = requests.post(url=f'{url}/sdapi/v1/txt2img', json=payload)
    r = response.json()
    image = Image.open(io.BytesIO(base64.b64decode(r['images'][0])))
    imageName = hashlib.md5(image.tobytes()).hexdigest() + '.png'
    image.save(imageName)
    return imageName


bot.run(token)