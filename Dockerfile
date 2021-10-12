FROM python

WORKDIR /proxy_server
COPY . .

RUN pip install -r requirements.txt

WORKDIR /proxy_server/src

EXPOSE 8080
EXPOSE 8000

CMD python main.py 0.0.0.0 8080 0.0.0.0 8000
