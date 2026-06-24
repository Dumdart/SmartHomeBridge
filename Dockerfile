FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.MD ./
COPY src ./src

RUN pip install --no-cache-dir .

USER 65532:65532

CMD ["smart-home-bridge"]
