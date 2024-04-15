import ast
import base64
import discord
import functools
import hashlib
import io
import json
import os
import requests
import subprocess
import typing
from discord import Intents
from discord.ext import commands
from dotenv import load_dotenv
from io import BytesIO
from PIL import Image, PngImagePlugin
from PIL.PngImagePlugin import PngInfo

load_dotenv()
token = os.getenv('TOKEN')
url = os.getenv('URL', 'http://localhost:7860/')
#batch_size_max = int(os.getenv('BATCH_SIZE_MAX', 1))
batch_count_max = int(os.getenv('BATCH_COUNT_MAX', 1))
max_upscale = int(os.getenv('MAX_UPSCALE', 1))
modelDict = ast.literal_eval(os.getenv('MODELS', '{}'))
vaeCompatibilityDict = ast.literal_eval(os.getenv('VAES_AND_COMPATIBILITY', '{}'))
allowedList = ast.literal_eval(os.getenv('ALLOWED', '[]'))
maximumValues = ast.literal_eval(os.getenv('MAX_VALUES', '{}'))
defaultValues = ast.literal_eval(os.getenv('DEFAULT_VALUES', '{}'))
samplers = ast.literal_eval(os.getenv('SAMPLERS', '{}'))
forbiddenPrompt = ast.literal_eval(os.getenv('FORBIDDEN_TERMS', '[]'))

intents = Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.command()
async def upscale(ctx, *args):
    try:
        attachment_url = ctx.message.attachments[0].url
    except:
        await ctx.send("No attachment present.")
        return
    file_request = requests.get(attachment_url)
    pil_image = Image.open(BytesIO(file_request.content))
    #pil_image = Image.open(img)
    payload = {
        "upscaling_resize": 1.5,
        "upscaler_1": "ESRGAN_4x",
        "image": pil_to_base64(pil_image)
}
    upscaled_image = await run_blocking(get_upscaled, payload, url)
    image = Image.open(io.BytesIO(base64.b64decode(upscaled_image.image)))

    png_payload = {
        "image": "data:image/png;base64," + i
    }
    response2 = requests.post(url=f'{url}/sdapi/v1/png-info', json=png_payload)

    pnginfo = PngImagePlugin.PngInfo()
    pnginfo.add_text("parameters", response2.json().get("info"))
    imageHash = str(hashlib.md5(image.tobytes()).hexdigest())
    image.save(imageHash + '.png', pnginfo=pnginfo)
    await ctx.send(file=discord.File(imageHash + ".png"))
    os.remove(imageHash + '.png')


@bot.command()
async def draw(ctx, *args):
    if isinstance(ctx.channel, discord.DMChannel):
            # Ignore direct messages
            return
    else:
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
        batch_count = get_batch_count(payload, batch_count_max)
        promptReady = ready_check(payload)
        if isReady and promptReady:
            for i in range(1, batch_count+1):
                try:
                    raw_image = await run_blocking(get_txt2img, payload, url)
                    info = get_image(raw_image, url)
                    print(json.dumps(info))
                    await ctx.send("Image " + str(i) + "/" + str(batch_count) +
                                   "\n`The user inputs for this image: " + str(payload) +
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

def get_upscaled(upscale_payload, url):
    response = requests.post(url=f'{url}/sdapi/v1/extra-single-image', json=upscale_payload)
    return response.json()

    return
def pil_to_base64(pil_image):
    with BytesIO() as stream:
        pil_image.save(stream, "PNG", pnginfo=None)
        base64_str = str(base64.b64encode(stream.getvalue()), "utf-8")
        return "data:image/png;base64," + base64_str

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

def get_image(raw_json, url):
    for i in raw_json['images']:
        image = Image.open(io.BytesIO(base64.b64decode(i.split(",", 1)[0])))

        png_payload = {
            "image": "data:image/png;base64," + i
        }
        response2 = requests.post(url=f'{url}/sdapi/v1/png-info', json=png_payload)

        pnginfo = PngImagePlugin.PngInfo()
        pnginfo.add_text("parameters", response2.json().get("info"))
        imageHash = str(hashlib.md5(image.tobytes()).hexdigest())
        image.save(imageHash + '.png', pnginfo=pnginfo)
    info = json.loads(raw_json["info"])
    info["ImgName"] = imageHash
    return info

def get_txt2img(payload, url):
    response = requests.post(url=f'{url}/sdapi/v1/txt2img', json=payload)
    return response.json()

def get_batch_count(payload, batch_count_max):
    batch_count_int = 1
    if 'batch_count' in payload:
        try:
            batch_count_int = int(payload['batch_count'])
        except:
            batch_count_int = 1
        if batch_count_int > batch_count_max:
            batch_count_int = batch_count_max
    return batch_count_int

async def run_blocking(blocking_func: typing.Callable, *args, **kwargs) -> typing.Any:
    """Runs a blocking function in a non-blocking way"""
    func = functools.partial(blocking_func, *args, **kwargs) # `run_in_executor` doesn't support kwargs, `functools.partial` does
    return await bot.loop.run_in_executor(None, func)

bot.run(token)
