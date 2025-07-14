FROM python:3.10-slim
WORKDIR /app
COPY . .
RUN apt-get update && apt-get install -y ffmpeg libsndfile1 && \
    pip install --upgrade pip && \
CMD ["python", "main.py"]