FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Generate protobuf files
RUN ./generate.sh

# Expose the gRPC port
EXPOSE 50053

# Set the default command
CMD ["python", "main.py"]
