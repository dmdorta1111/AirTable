# =============================================================================
# PyBase Frontend Dockerfile
# Multi-stage build for React production image with nginx
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Build stage
# -----------------------------------------------------------------------------
FROM node:20-alpine as builder

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production && \
    npm cache clean --force

# Copy source code
COPY . .

# Build React application
RUN npm run build

# -----------------------------------------------------------------------------
# Stage 2: Production stage
# -----------------------------------------------------------------------------
FROM nginx:alpine as production

# Install curl for health check
RUN apk add --no-cache curl

# Create non-root user
RUN addgroup --gid 1000 --system nginx-user && \
    adduser --uid 1000 --system --ingroup nginx-user nginx-user

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Copy built files from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Set proper permissions
RUN chown -R nginx-user:nginx-user /usr/share/nginx/html && \
    chown -R nginx-user:nginx-user /var/cache/nginx && \
    chown -R nginx-user:nginx-user /var/log/nginx && \
    chown -R nginx-user:nginx-user /etc/nginx/conf.d && \
    mkdir -p /var/run && \
    chown -R nginx-user:nginx-user /var/run/nginx.pid

# Switch to non-root user
USER nginx-user

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]

# -----------------------------------------------------------------------------
# Stage 3: Development stage
# -----------------------------------------------------------------------------
FROM node:20-alpine as development

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install all dependencies (including dev dependencies)
RUN npm install && \
    npm cache clean --force

# Copy source code
COPY . .

# Expose port
EXPOSE 5173

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5173/ || exit 1

# Start Vite dev server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
