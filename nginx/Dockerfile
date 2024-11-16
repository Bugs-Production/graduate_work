FROM nginx:latest

RUN rm /etc/nginx/conf.d/default.conf
RUN rm /etc/nginx/nginx.conf

COPY site.conf /etc/nginx/conf.d/site.conf
COPY nginx.conf /etc/nginx/nginx.conf
