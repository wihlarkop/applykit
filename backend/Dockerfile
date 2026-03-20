FROM python:3.12-slim

# Install WeasyPrint system dependencies
RUN apt-get update && apt-get install -y \
    libcairo2 \
    libpango-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi7 \
    shared-mime-info \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    libjpeg-dev \
    libtiff-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy backend files
COPY . .

# Install Python dependencies
RUN pip install uv && uv sync

EXPOSE 8000

CMD ["uv", "run", "main.py"]
