FROM python:3.10-alpine

RUN apk upgrade --no-cache

RUN addgroup --gid 20001 --system nonroot && \
    adduser --uid 10001 --system --ingroup nonroot --disabled-password --gecos "" nonroot && \
    pip install --upgrade pip

COPY --chown=nonroot:nonroot src src

WORKDIR src
COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

USER nonroot:nonroot

ARG APP_VERSION
ENV APP_VERSION=$APP_VERSION

ENTRYPOINT ["fastapi", "run", "main.py", "--port", "8080"]
