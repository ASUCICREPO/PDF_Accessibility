# Stage 1: Build stage with build dependencies
FROM public.ecr.aws/docker/library/node:22-slim AS builder

WORKDIR /app

# Install build dependencies (only needed for compiling native modules)
RUN apt-get update && apt-get install -y \
    build-essential \
    python3 \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy package files and install dependencies
COPY package*.json ./
RUN npm install --omit=dev

# Stage 2: Production stage with minimal runtime
FROM public.ecr.aws/docker/library/node:22-slim

WORKDIR /app

# Install only runtime dependencies for better-sqlite3
RUN apt-get update && apt-get install -y \
    libsqlite3-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy node_modules from builder stage
COPY --from=builder /app/node_modules ./node_modules

# Copy application source code
COPY . .

# Define the command to run the app
CMD ["node", "alt_text_generator.js"]
