import ast
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
modelDict = ast.literal_eval(os.getenv('MODELS'))
disallowedList = ast.literal_eval(os.getenv('DISALLOWED'))

intents = Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.command()
async def draw(ctx, *args):
    payload = build_payload(' '. join(args), modelDict)
    imageName = get_image(payload, url)
    await ctx.send(str(payload), file=discord.File(imageName))
    os.remove(imageName)

#trims max size for certain variables
def trim_payload(dirtyPayload):

    return cleanPayload

def build_payload(input, modelDict):
    parts = input.split('|')
    trimmedParts = [s.strip() for s in parts]
    filteredDict = {s.split(maxsplit=1)[0]: s.split(maxsplit=1)[1] for s in trimmedParts if
                    ':' in s.split(maxsplit=1)[0]}
    lowercaseDict = {key.lower(): value.lower() for key, value in filteredDict.items()}
    payload = {key.replace(':', ''): value for key, value in lowercaseDict.items()}

    if 'model' in payload:
        if payload.get('model') in modelDict:
            override_settings = {
                "sd_model_checkpoint": modelDict.get(payload.get('model'))
            }
            payload["override_settings"] = override_settings

    return payload

def get_image(payload, url):
    response = requests.post(url=f'{url}/sdapi/v1/txt2img', json=payload)
    r = response.json()
    image = Image.open(io.BytesIO(base64.b64decode(r['images'][0])))
    imageName = hashlib.md5(image.tobytes()).hexdigest() + '.png'
    image.save(imageName)
    return imageName


bot.run(token)