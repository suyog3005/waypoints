FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . /app

# Copy the shared db package from repo root
COPY ../db /app/db
COPY ../contracts /app/contracts

# Install dependencies
RUN pip install --no-cache-dir -e /app/db
RUN pip install --no-cache-dir -e /app/contracts
RUN pip install --no-cache-dir -r /app/requirements.txt

# Set PYTHONPATH to include repo root
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Run uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
