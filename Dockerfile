FROM python:3.13-slim

WORKDIR /app

ENV POETRY_VIRTUALENVS_CREATE=false

RUN pip install poetry

COPY pyproject.toml poetry.lock ./

RUN poetry install --only main --no-interaction --no-ansi

COPY . .

CMD ["python", "-m", "app.main"]