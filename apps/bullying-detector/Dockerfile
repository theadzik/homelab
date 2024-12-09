FROM python:3.12

WORKDIR /src
COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY src/main.py main.py
RUN python3 -c "import main" # Importing module to download data needed to run.

ENTRYPOINT ["fastapi", "run", "main.py", "--port", "8080"]
