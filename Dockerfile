FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY agent ./agent
COPY database ./database

# Expose FastAPI port
EXPOSE 8000

# Start FastAPI server + lifespan background worker
CMD ["uvicorn", "agent.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
