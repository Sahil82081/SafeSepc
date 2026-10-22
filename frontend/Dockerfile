# Multi-stage Dockerfile for SafeSpec React/Vite Frontend
FROM node:22-alpine AS builder

WORKDIR /app

# Install dependencies first for Docker caching
COPY package.json package-lock.json* ./
RUN npm install

# Copy application source code
COPY . ./

# Build production bundle
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build

# Stage 2: Minimal production web server
FROM nginx:alpine

# Copy nginx config for single page application routing
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy build artifacts to nginx public folder
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
