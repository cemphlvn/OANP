FROM python:3.11-slim AS base

# Install Node.js 20.x from NodeSource
RUN apt-get update \
  && apt-get install -y --no-install-recommends curl ca-certificates \
  && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
  && apt-get install -y --no-install-recommends nodejs \
  && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files first (layer caching)
COPY package.json package-lock.json* ./
COPY pyproject.toml uv.lock* ./

# Install dependencies
RUN npm ci || npm install
RUN uv sync --no-dev

# Copy project source
COPY . .

# Build frontend if it exists
RUN if [ -d "src/frontend" ]; then cd src/frontend && npm ci && npm run build; fi

EXPOSE 3000 8123

CMD ["npm", "run", "dev"]
