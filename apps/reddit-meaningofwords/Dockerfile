FROM python:3.12-alpine

RUN apk upgrade --no-cache

RUN addgroup --gid 20001 --system nonroot && \
    adduser --uid 10001 --system --ingroup nonroot --disabled-password --no-create-home --gecos "" nonroot && \
    pip install --upgrade pip

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY --chown=nonroot:nonroot src src

USER nonroot:nonroot

ARG APP_VERSION
ENV APP_VERSION=$APP_VERSION

ENTRYPOINT ["python", "src/main.py"]
