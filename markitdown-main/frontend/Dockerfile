# ==============================================================================
# MarkItDown Frontend Service Dockerfile
# Serves HTML + Vue3 + Axios Web UI and Nginx Reverse Proxy for Backend API
# ==============================================================================

FROM nginx:alpine

# Metadata
LABEL maintainer="MarkItDown Team"
LABEL description="HTML/Vue3 + Axios frontend client for MarkItDown platform with Nginx proxy"

# Clean default static files
RUN rm -rf /usr/share/nginx/html/*

# Copy static frontend files (index.html, src/, components, assets) to web root
COPY . /usr/share/nginx/html/

# Copy Nginx server configuration with /api/ reverse proxy to markitdown-backend
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 8080 as requested
EXPOSE 8080

# Container health check using built-in busybox wget
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD wget -q -O - http://localhost:8080/ || exit 1

# Run Nginx in foreground
CMD ["nginx", "-g", "daemon off;"]
