FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv
COPY pyproject.toml ./
RUN mkdir app seeds && pip install --no-cache-dir -e ".[dev]"
COPY . .
RUN useradd -r -u 10001 appuser && mkdir -p /data/storage && chown -R appuser /srv /data/storage
USER appuser
EXPOSE 8090
CMD ["./start.sh", "--workers", "2"]
