FROM python:3.14-slim

RUN apt-get update \
    && apt-get install -y curl \
    && rm -rf /var/lib/apt/lists/*

COPY ./pyproject.toml ./
COPY ./README.md ./
COPY ./app /app

RUN pip install .

WORKDIR /app

ENTRYPOINT ["python"]

CMD ["-m", "app.main"]
