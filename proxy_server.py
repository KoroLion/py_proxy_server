import os
import sys
import socket
import shutil
from threading import Thread, Lock
from pathlib import Path
import ssl
from urllib.parse import urlparse
import sqlite3
import json

from flask import Flask

from utils.http_utils import receive_http, HttpPacket, CONNECTION_ESTABLISHED_RESPONSE
from utils.cert_utils import generate_cert, generate_root_cert
from utils.db_utils import create_tables, save_to_db
from utils.file_utils import read_file

CERTS_PATH = './certs'

ROOT_CA_NAME = 'LioKor Proxy CA'
ROOT_CA_CRT = './root_cert/ca.crt'
ROOT_CA_KEY = './root_cert/ca.key'
ROOT_CERT_KEY = './root_cert/cert.key'

HOST = '127.0.0.1'
PORT = 8000


# con = sqlite3.connect(':memory:', check_same_thread=False)
con = sqlite3.connect('wolf.sqlite', check_same_thread=False)
mutex = Lock()

app = Flask(__name__)

@app.route('/api/requests')
def api_requests_page():
    cur = con.cursor()
    cur.execute('SELECT id, time, protocol, method, url, request, response FROM requests ORDER BY id DESC')
    data = cur.fetchall()
    parsed_data = []
    for entry in data:
        parsed_data.append({
            'id': entry[0],
            'time': entry[1],
            'protocol': entry[2],
            'method': entry[3],
            'url': entry[4],
            'request': entry[5],
            'response': entry[6]
        })

    return json.dumps(parsed_data)


@app.route('/api/requests/<id>')
def api_request_page(id):
    cur = con.cursor()
    cur.execute('SELECT id, time, protocol, method, url, request, response FROM requests WHERE id = ?', (int(id), ))
    data = cur.fetchall()
    entry = data[0]
    request = {
        'id': entry[0],
        'time': entry[1],
        'protocol': entry[2],
        'method': entry[3],
        'url': entry[4],
        'request': entry[5],
        'response': entry[6]
    }

    return json.dumps(request)


@app.route('/requests')
def requests_page():
    template = read_file('./templates/requests.html')
    return template


@app.route('/requests/<id>')
def request_page(id):
    template = read_file('./templates/request.html')
    return template


def prepare_https(http_packet: HttpPacket, client_sock) -> (socket.socket, HttpPacket, tuple):
    client_sock.sendall(CONNECTION_ESTABLISHED_RESPONSE)
    host, port = http_packet.url.split(':')
    host_addr = (host, int(port))

    cert_path = '{}/{}.crt'.format(CERTS_PATH, host)
    if not Path(cert_path).is_file():
        cert = generate_cert(host, ROOT_CA_CRT, ROOT_CA_KEY, ROOT_CERT_KEY)
        f = open(cert_path, 'w')
        f.write(cert.decode())
        f.close()

    client_sock = ssl.wrap_socket(client_sock, keyfile=ROOT_CERT_KEY, certfile=cert_path, server_side=True)

    http_packet = receive_http(client_sock)

    return client_sock, http_packet, host_addr


def prepare_http(http_packet: HttpPacket) -> (HttpPacket, tuple):
    url = urlparse(http_packet.url)

    host = url.hostname
    port = 80 if url.port is None else url.port
    host_addr = (host, port)

    if http_packet.headers.get('Proxy-Connection', None):
        del http_packet.headers['Proxy-Connection']

    path = url.path
    if url.query:
        path += '?' + url.query
    http_packet.start_line = ' '.join([http_packet.method, path, http_packet.protocol])

    return http_packet, host_addr


def handle_connection(client_sock, addr, con):
    request = receive_http(client_sock)

    host_addr = (None, None)
    https = False

    if request.method == 'CONNECT':
        https = True
        try:
            client_sock, request, host_addr = prepare_https(request, client_sock)
        except Exception as e:
            print('ERROR: while trying to establish https connection')
            client_sock.close()
            return
    else:
        request, host_addr = prepare_http(request)

    new_request = request.encode()

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.connect(host_addr)
    if https:
        server_sock = ssl.wrap_socket(server_sock)

    server_sock.sendall(new_request)

    response = receive_http(server_sock)
    server_sock.close()

    protocol = 'https' if https else 'http'
    save_to_db(con, mutex, protocol, request.method, request.url, str(request), str(response))

    new_response = response.encode()

    client_sock.sendall(new_response)
    client_sock.close()


def main():
    host, port = HOST, PORT

    if len(sys.argv) > 1:
        host = sys.argv[1]
    if len(sys.argv) > 2:
        port = int(sys.argv[2])

    cert_path_split = ROOT_CERT_KEY.split('/')
    base_ca_path = '/'.join(cert_path_split[:len(cert_path_split) - 1])
    if not Path(base_ca_path).exists():
        shutil.rmtree(CERTS_PATH)
        os.makedirs(base_ca_path)
        generate_root_cert(ROOT_CA_NAME, ROOT_CA_CRT, ROOT_CA_KEY, ROOT_CERT_KEY)

    if not Path(CERTS_PATH).exists():
        os.makedirs(CERTS_PATH)

    create_tables(con)

    flask_thread = Thread(target=app.run, kwargs={'host': host, 'port': 8080})
    flask_thread.start()

    serv = socket.create_server((host, port))
    serv.listen(32)
    print('Proxy serving at {}:{}'.format(host, port))
    while True:
        sock, addr = serv.accept()
        print('Connection from {}'.format(addr))
        thread = Thread(target=handle_connection, args=(sock, addr, con, ))
        thread.start()


if __name__ == '__main__':
    main()
