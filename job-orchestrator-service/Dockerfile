FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY proto/ proto/
COPY server/ server/
COPY generated/ generated/
COPY generate.sh .

# Generate gRPC code
RUN chmod +x generate.sh && ./generate.sh

# Expose gRPC port
EXPOSE 50055

# Run server (unbuffered for immediate log output)
CMD ["python", "-u", "-m", "server.main"]
