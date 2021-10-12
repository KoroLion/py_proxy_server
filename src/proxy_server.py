import socket
from threading import Thread
from pathlib import Path
import ssl
from urllib.parse import urlparse
import shutil
import os

from settings import CERTS_PATH, ROOT_CA_NAME, ROOT_CA_CRT, ROOT_CA_KEY, ROOT_CERT_KEY

from utils.http_utils import send_request, receive_http, HttpPacket, CONNECTION_ESTABLISHED_RESPONSE
from utils.cert_utils import generate_cert, generate_root_cert
from utils.db_utils import save_to_db


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
    http_packet.url = 'https://{}{}'.format(host, http_packet.url)

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


def handle_connection(client_sock, addr, con, mutex):
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

    response = send_request(host_addr, new_request, https)

    protocol = 'https' if https else 'http'
    save_to_db(con, mutex, protocol, request.method, request.url, str(request), str(response))

    new_response = response.encode()

    client_sock.sendall(new_response)
    client_sock.close()


def run_proxy_app(host, port, con, mutex):
    cert_path_split = ROOT_CERT_KEY.split('/')
    base_ca_path = '/'.join(cert_path_split[:len(cert_path_split) - 1])
    if not Path(base_ca_path).exists():
        shutil.rmtree(CERTS_PATH)
        os.makedirs(base_ca_path)
        generate_root_cert(ROOT_CA_NAME, ROOT_CA_CRT, ROOT_CA_KEY, ROOT_CERT_KEY)

    if not Path(CERTS_PATH).exists():
        os.makedirs(CERTS_PATH)

    serv = socket.create_server((host, port))
    serv.listen(32)
    print('Proxy serving at {}:{}'.format(host, port))
    while True:
        sock, addr = serv.accept()
        print('Connection from {}'.format(addr))
        thread = Thread(target=handle_connection, args=(sock, addr, con, mutex, ))
        thread.start()
