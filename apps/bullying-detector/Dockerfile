FROM python:3.13

WORKDIR /src
COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY src/main.py main.py

USER 10005


RUN python -c "from fastapi import FastAPI;from fastapi import status;from pydantic import BaseModel;from transformers import pipeline"
ENTRYPOINT ["fastapi", "run", "main.py", "--port", "8080"]
