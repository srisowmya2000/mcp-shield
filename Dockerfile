FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn pydantic pydantic-settings mcp httpx pyyaml rich
COPY runtime/ ./runtime/
COPY policies/ ./policies/
RUN mkdir -p /app/reports
EXPOSE 8000
CMD ["uvicorn", "runtime.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
