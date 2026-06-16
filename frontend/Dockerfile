# ==========================================================================
# BomaSec — Next.js Frontend Dockerfile
# ==========================================================================
FROM node:20-alpine AS base

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm install

# Copy application code
COPY . .

# Expose Next.js dev port
EXPOSE 3000

# Default: run Next.js dev server
CMD ["npm", "run", "dev"]
