FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for advanced PDF module bindings
RUN apt-get update && apt-get install -y \
    wkhtmltopdf \
    tesseract-ocr \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    ghostscript \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Ensure file system structure exists for Flask
RUN mkdir -p uploads outputs

COPY . .

# EXPOSE is not strictly needed for Render but good for documentation. 
# Render will map to the port gunicorn binds to.
EXPOSE 5000

# Using Gunicorn for production-grade serving
# Using Gunicorn for production-grade serving. 
# We use the shell form to allow $PORT substitution from Render.
CMD gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 3 --timeout 120 app:app
