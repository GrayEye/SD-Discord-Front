# Use the official Python 3.11 Slim Bullseye image as base
FROM python:3.11-slim-bullseye

# Install required system dependencies for pngquant
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpng-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Install pngquant
RUN apt-get update && apt-get install -y --no-install-recommends pngquant

# Continue with your Dockerfile instructions...


RUN pip install -r requirements.txt

CMD ["python", "bot.py"]
