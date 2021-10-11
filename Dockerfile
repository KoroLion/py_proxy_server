FROM python

WORKDIR /proxy_server
COPY . .

EXPOSE 8080

CMD python proxy_server.py 0.0.0.0 8080
