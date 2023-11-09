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
maximumValues = ast.literal_eval(os.getenv('MAX_VALUES'))
defaultValues = ast.literal_eval(os.getenv('DEFAULT_VALUES'))
samplers = ast.literal_eval(os.getenv('SAMPLERS'))

intents = Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.command()
async def draw(ctx, *args):
    payload = build_payload(' '. join(args), modelDict, samplers)
    payload = remove_disallowed_payload(payload, disallowedList)
    payload = set_maximums(payload, maximumValues)
    payload = set_defaults(payload, defaultValues)
    imageName = get_image(payload, url)
    await ctx.send("The inputs for this image: " + str(payload), file=discord.File(imageName))
    os.remove(imageName)

# Removes disallowed api requests
def remove_disallowed_payload(payload, disallowedList):
    items_to_remove = []
    for item in disallowedList:
        if item in payload:
            items_to_remove.append(item)
    for item in items_to_remove:
        del payload[item]
    return payload

# Set maximum values and round floats where not allowed
def set_maximums(payload, maximumValues):
    for key in payload:
        if key == "cfg_scale":
            if float(payload[key]) > maximumValues[key]:
                payload[key] = str(maximumValues[key])
            else:
                continue
        if key in maximumValues and int(round(float(payload[key]))) > maximumValues[key]:
            payload[key] = str(maximumValues[key])
    print(payload)
    return payload

def set_defaults(payload, defaultValues):
    for key in defaultValues:
        if key not in payload:
            payload[key] = defaultValues[key]
    return payload

def build_payload(input, modelDict, samplers):
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
        else:
            payload['model'] = modelDict['default']
    else:
        payload['model'] = modelDict['default']

    if 'sampler' in payload:
        if payload.get('sampler') in samplers:
            payload["sampler_name"] = samplers.get(payload.get('sampler'))
        else:
            payload["sampler_name"] = samplers.get('default')
    else:
        payload["sampler_name"] = samplers.get('default')
    return payload

def get_image(payload, url):
    response = requests.post(url=f'{url}/sdapi/v1/txt2img', json=payload)
    r = response.json()
    image = Image.open(io.BytesIO(base64.b64decode(r['images'][0])))
    imageName = hashlib.md5(image.tobytes()).hexdigest() + '.png'
    image.save(imageName)
    return imageName

bot.run(token)