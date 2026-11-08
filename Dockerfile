FROM python:3.13-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000
CMD ["gunicorn", "--preload", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]