# Base image
FROM python:3.11-slim

# Working directory
WORKDIR /app

# Dependencies copy
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Command to run your serve.py
CMD ["python", "serve.py"]
