FROM --platform="linux/arm64" python:3.10-alpine

COPY src src
COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

WORKDIR src
ENTRYPOINT ["python", "update.py"]