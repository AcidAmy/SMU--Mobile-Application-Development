# Frontend Dockerfile for MarkItDown (Section 5.4)
FROM nginx:alpine

# Copy static frontend files to Nginx html directory
COPY . /usr/share/nginx/html/

# Copy Nginx server configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
