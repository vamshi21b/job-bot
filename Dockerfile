FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy
WORKDIR /app
COPY requirements.txt .
# Install PDF rendering engine and its dependencies
RUN apt-get update && apt-get install -y wkhtmltopdf
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "main.py"]