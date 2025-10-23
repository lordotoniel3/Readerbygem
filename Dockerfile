# Dockerfile
FROM python:3.12-slim
RUN pip install uv
# This is for the python-magic library
RUN apt-get update && apt-get install -y \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml .
COPY uv.lock .
COPY app ./app
COPY analyzers ./analyzers
COPY prompts ./prompts

RUN uv sync

EXPOSE 8000
CMD ["uv","run","fastapi", "run", "app/main.py"]