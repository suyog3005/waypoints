FROM python:3.12-slim

WORKDIR /app

# LightGBM's compiled core links against libgomp (OpenMP) at runtime, which
# the slim base image doesn't include.
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt
COPY api/requirements.txt ./api-requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r api-requirements.txt

# src/ and models/ are volume-mounted by docker-compose.yml, not baked in
# here, so pipeline edits and retrained models show up without a rebuild.
COPY api/ ./api/

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
