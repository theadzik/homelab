FROM python:3.12

WORKDIR /src
COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY src/main.py main.py

USER 10005

ENTRYPOINT ["fastapi", "run", "main.py", "--port", "8080"]
