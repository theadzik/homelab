FROM python:3.13-alpine

RUN apk add --no-cache sqlite

RUN addgroup --gid 20005 --system nonroot && \
    adduser --uid 10005 --system --ingroup nonroot --disabled-password --gecos "" nonroot

COPY --chown=nonroot:nonroot src /src

WORKDIR /src
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

USER nonroot:nonroot

ARG APP_VERSION="alpha"
ENV APP_VERSION=$APP_VERSION

ENTRYPOINT ["python", "main.py"]
