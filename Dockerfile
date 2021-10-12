FROM python

WORKDIR /proxy_server/src
COPY . .

RUN pip install -r ../requirements.txt

EXPOSE 8080
EXPOSE 8000

CMD python main.py 0.0.0.0 8080 0.0.0.0 8000
