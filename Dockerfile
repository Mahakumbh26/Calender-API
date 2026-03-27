FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Non-root user for security
RUN adduser --disabled-password --gecos "" appuser
USER appuser

# Expose port (Railway injects $PORT at runtime)
EXPOSE 8000

# Gunicorn: 4 workers, each with 2 threads — handles concurrent requests well
CMD ["sh", "-c", "gunicorn --workers 4 --threads 2 --worker-class gthread --bind 0.0.0.0:${PORT:-8000} --timeout 60 --access-logfile - --error-logfile - app:app"]
