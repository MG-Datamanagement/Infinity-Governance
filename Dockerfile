FROM python:3.11-slim
WORKDIR /app

# Install system dependencies and uv
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    gnupg2 \
    apt-transport-https \
    ca-certificates \
    unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Microsoft ODBC Driver 18 for SQL Server
RUN curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
        | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
        > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 \
    && apt-get clean \
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
