FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy
WORKDIR /app
COPY requirements.txt .
# 1. Force non-interactive mode globally
ENV DEBIAN_FRONTEND=noninteractive
# 2. Feed it a default timezone so it doesn't ask
ENV TZ=America/Chicago

# 3. Install the PDF rendering engine
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    wkhtmltopdf \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "main.py"]