# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

RUN addgroup --system kisanpath && adduser --system --ingroup kisanpath kisanpath
COPY pyproject.toml README.md alembic.ini ./
COPY src ./src
COPY migrations ./migrations
COPY examples ./examples
RUN pip install --no-cache-dir .

USER kisanpath
EXPOSE 8000
CMD ["uvicorn", "kisanpath.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
