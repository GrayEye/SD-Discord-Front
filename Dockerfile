FROM python:3.11-slim-bullseye

COPY . /app
WORKDIR /app

RUN pip install -r requirments.txt