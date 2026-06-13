FROM python:3.11-slim

WORKDIR /app

# Setup environment
ENV PYTHONPATH=/app
ENV SREEBASE_DATA_DIR=/app/data

# Copy the core database application
COPY sreebase /app/sreebase

# Create a volume-mountable data directory
RUN mkdir -p /app/data

EXPOSE 6969

CMD ["python", "-m", "sreebase.server.tcp_server", "--host", "0.0.0.0", "--port", "6969", "--data-dir", "/app/data"]
