FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for scanpy / HDF5
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ libhdf5-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "main:app", "-w", "2", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000", "--timeout", "300"]
