FROM nginxinc/nginx-unprivileged:1.31.7-alpine3.24

USER root
RUN apk update && apk upgrade --no-cache && rm -rf /var/cache/apk/*

COPY nginx.conf /etc/nginx/nginx.conf
COPY index.html /usr/share/nginx/html/index.html

USER 101
EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]