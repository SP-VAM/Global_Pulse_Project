# ==============================================================================
# GlobalPulse Frontend Dockerfile
# Multi-stage build: Node 18 build stage -> Nginx Alpine production runner
# ==============================================================================

# Build Stage
FROM node:18-alpine AS builder

WORKDIR /app

# Pass build-time environment variable for VITE_API_BASE_URL
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Production Runner Stage
FROM nginx:alpine AS runner

# Copy custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy static bundle from build stage
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
