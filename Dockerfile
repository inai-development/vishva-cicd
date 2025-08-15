
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg libsndfile1 ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create non-root user and switch to it (for security)
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Entrypoint
CMD ["python", "serve.py"]
