FROM --platform="linux/arm64" python:3.10-alpine

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY src src

WORKDIR src
ENTRYPOINT ["python", "update.py"]