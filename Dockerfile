FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

# Install runtime dependencies
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY src/ ./src/
COPY backend/data/ ./backend/data/

EXPOSE 8000

CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
