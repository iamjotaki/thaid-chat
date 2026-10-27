FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Bangkok

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Ensure data and static directories exist
RUN mkdir -p data static

EXPOSE 8094

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8094"]
