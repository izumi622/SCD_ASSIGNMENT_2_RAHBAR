FROM nginxinc/nginx-unprivileged:1.31.7-alpine3.24
COPY nginx.conf /etc/nginx/nginx.conf
COPY index.html /usr/share/nginx/html/index.html
USER 101
EXPOSE 8080

# Explicit exec-form command to preserve SIGTERM handling.
CMD ["nginx", "-g", "daemon off;"]
