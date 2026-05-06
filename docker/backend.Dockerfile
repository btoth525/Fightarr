FROM python:3.11-slim

WORKDIR /app

# System deps for lxml/html parsing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 7878

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7878", "--reload"]
