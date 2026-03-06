FROM python:3.11-slim
WORKDIR /app

# Install system dependencies and uv
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Copy requirements first → excellent caching when deps don't change
COPY requirements.txt .
COPY index_to_solr.py .       
COPY configure_solr_schema.sh .
COPY services/ ./services/


# Install Python dependencies using uv
RUN uv pip install --system -r requirements.txt

# Copy your app code and package (changes most often)
COPY app.py .
# COPY app/ ./app/

# # Make sure the app can find its modules
# ENV PYTHONPATH=/app

EXPOSE 8005

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8005/health || exit 1

CMD ["python", "app.py"]



# FROM python:3.11-slim
# WORKDIR /app
# # Install system dependencies
# RUN apt-get update && apt-get install -y \
#     postgresql-client \
#     && rm -rf /var/lib/apt/lists/*
# # Copy requirements and install Python dependencies
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt
# # Copy application
# COPY app.py .
# # Create results directory for chat history
# RUN mkdir -p /app/results
# # Expose port
# EXPOSE 8005
# # Health check
# HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
#     CMD curl -f http://localhost:8005/health || exit 1
# # Run the application
# CMD ["python", "app.py"]
