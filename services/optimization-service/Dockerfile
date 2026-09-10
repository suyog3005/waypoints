FROM python:3.12-slim

WORKDIR /app

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

# Run the Kafka consumer loop (no HTTP server)
CMD ["python", "-m", "app.main"]
