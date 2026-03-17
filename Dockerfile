FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy
WORKDIR /app
COPY requirements.txt .
# Suppress interactive prompts and install wkhtmltopdf
RUN DEBIAN_FRONTEND=noninteractive apt-get update && \
    apt-get install -y --no-install-recommends tzdata wkhtmltopdf
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "main.py"]