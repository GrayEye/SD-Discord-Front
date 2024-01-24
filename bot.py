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
from PIL.PngImagePlugin import PngInfo

load_dotenv()
token = os.getenv('TOKEN')
url = os.getenv('URL')
modelDict = ast.literal_eval(os.getenv('MODELS'))
vaeCompatibilityDict = ast.literal_eval(os.getenv('VAES_AND_COMPATIBILITY'))
#disallowedList = ast.literal_eval(os.getenv('DISALLOWED'))
allowedList = ast.literal_eval(os.getenv('ALLOWED'))
maximumValues = ast.literal_eval(os.getenv('MAX_VALUES'))
defaultValues = ast.literal_eval(os.getenv('DEFAULT_VALUES'))
samplers = ast.literal_eval(os.getenv('SAMPLERS'))
forbiddenPrompt = ast.literal_eval(os.getenv('FORBIDDEN_TERMS'))

intents = Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.command()
async def draw(ctx, *args):
    isReady = True
    try:
        payload = build_payload(' '. join(args), samplers)
    except:
        isReady = False
        await ctx.send("Payload generation Failed. Likely blank `!draw` command.")
        return
    payload = remove_invalid_payload(payload, allowedList)
    payload = set_maximums(payload, maximumValues)
    payload = set_defaults(payload, defaultValues)
    payload = add_model(payload, modelDict)
    payload = add_vae(payload, vaeCompatibilityDict)
    promptReady = ready_check(payload)
    if isReady and promptReady:
        try:
            info = get_image(get_txt2img(payload, url))
            print(json.dumps(info))
            await ctx.send("`The user inputs for this image: " + str(payload) +
                           "\nSeed: " + str(info["seed"]) +
                           "\nSubseed: " + str(info["subseed"]) + "`",
                           file=discord.File(info["ImgName"] + ".png"))
            os.remove(info["ImgName"] + '.png')
        except:
            await ctx.send("Image generation failed. Inputs used for this attempt: " + str(payload))
    else:
        errorMessage = "Image generation failed."
        if not promptReady:
            errorMessage = errorMessage + " No prompt, blank prompt, or misspelled the key 'prompt'."
        await ctx.send(errorMessage + " Try again or contact bot owner if issues persist.")

#Remove disallowed prompts and ensure no blank items in a prompt
def sanitize_prompt(payload, forbiddenPrompt):
    prompts = payload["prompt"].split(', ')
    sanitized_items = [item for item in prompts if item not in forbiddenPrompt]
    payload["prompt"] = ', '.join(sanitized_items)
    if "negative_prompt" in payload:
        negPrompts = payload["negative_prompt"].split(', ')
        payload["negative_prompt"] = ', '.join(negPrompts)
    return payload

def ready_check(payload):
    status = False
    if "prompt" in payload and payload["prompt"]:
        status = True
    return status

# Removes disallowed api requests
def remove_invalid_payload(payload, allowedList):
    items_to_remove =[]
    for key in payload:
        if key not in allowedList:
            items_to_remove.append(key)
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
        if key in maximumValues:
            payload[key] = int(round(float(payload[key])))
            if payload[key] > maximumValues[key]:
                payload[key] = str(maximumValues[key])
            payload[key] = str(payload[key])
    return payload

def set_defaults(payload, defaultValues):
    for key in defaultValues:
        if key not in payload:
            payload[key] = defaultValues[key]
    return payload

#Manipulates raw user input
def build_payload(input, samplers):
    parts = input.split('|')
    trimmedParts = [s.strip() for s in parts]
    payload = {}
    for item in trimmedParts:
        key, value = item.split(':', 1)
        key = key.strip().lower()
        value = value.strip().lower()
        payload[key] = value
    if 'sampler' in payload:
        if payload.get('sampler') in samplers:
            payload["sampler_name"] = samplers.get(payload.get('sampler'))
        else:
            payload["sampler_name"] = samplers.get('default')
    else:
        payload["sampler_name"] = samplers.get('default')
    return payload

def add_model(payload, modelDict):
    if 'model' in payload:
        if payload.get('model') in modelDict:
            overrideSettings = {
                "sd_model_checkpoint": modelDict.get(payload.get('model'))
            }
            payload["override_settings"] = overrideSettings
        else:
            override_settings = {
                "sd_model_checkpoint": modelDict.get('default')
            }
            payload["override_settings"] = override_settings
            payload['model'] = modelDict['default']
    else:
        overrideSettings = {
            "sd_model_checkpoint": modelDict.get('default')
        }
        payload["override_settings"] = overrideSettings
        payload['model'] = modelDict['default']
    return payload

def add_vae(payload, vaeDict):
    vae = "None"
    overrideSettings = payload.get("override_settings")
    model = overrideSettings.get("sd_model_checkpoint")
    for key, values in vaeDict.items():
        if model in values:
            vae = key
    overrideSettings["sd_vae"] = vae
    payload["override_settings"] = overrideSettings
    return payload

def get_image(raw_json):
    image = Image.open(io.BytesIO(base64.b64decode(raw_json['images'][0])))
    info = json.loads(raw_json["info"])
    metadata = PngInfo()
    metadata.add_text(b"Generation Data", json.dumps(info).encode("latin-1", "strict"))
    imageHash = str(hashlib.md5(image.tobytes()).hexdigest())
    image.save(imageHash + '.png', pnginfo=metadata)
    info["ImgName"] = imageHash
    return info

def get_txt2img(payload, url):
    response = requests.post(url=f'{url}/sdapi/v1/txt2img', json=payload)
    return response.json()

bot.run(token)
