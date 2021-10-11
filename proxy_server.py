import os
import sys
import socket
import shutil
from threading import Thread
from pathlib import Path
import ssl
from urllib.parse import urlparse

from http_utils import receive_http, HttpPacket, CONNECTION_ESTABLISHED_RESPONSE
from cert_utils import generate_cert, generate_root_cert

CERTS_PATH = './certs'
ROOT_CA_CRT = './root_cert/ca.crt'
ROOT_CA_KEY = './root_cert/ca.key'
ROOT_CERT_KEY = './root_cert/cert.key'

HOST = '127.0.0.1'
PORT = 8000


def prepare_https(http_packet: HttpPacket, client_sock) -> (socket.socket, HttpPacket, tuple):
    method, url, protocol = http_packet.start_line.split(' ', 2)

    client_sock.sendall(CONNECTION_ESTABLISHED_RESPONSE)
    host, port = url.split(':')
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
    method, url, protocol = http_packet.start_line.split(' ', 2)

    url = urlparse(url)

    host = url.hostname
    port = 80 if url.port is None else url.port
    host_addr = (host, port)

    if http_packet.headers.get('Proxy-Connection', None):
        del http_packet.headers['Proxy-Connection']

    path = url.path
    if url.query:
        path += '?' + url.query
    http_packet.start_line = ' '.join([method, path, protocol])

    return http_packet, host_addr


def handle_connection(client_sock, addr):
    http_packet = receive_http(client_sock)
    method, url, protocol = http_packet.start_line.split(' ', 2)

    host_addr = (None, None)
    https = False

    if method == 'CONNECT':
        https = True
        client_sock, http_packet, host_addr = prepare_https(http_packet, client_sock)
    else:
        print(http_packet.start_line)
        http_packet, host_addr = prepare_http(http_packet)
        print(http_packet.start_line)

    new_request = http_packet.encode()
    # print(new_request)

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.connect(host_addr)
    if https:
        server_sock = ssl.wrap_socket(server_sock)

    server_sock.sendall(new_request)

    http_packet = receive_http(server_sock)
    server_sock.close()

    new_response = http_packet.encode()

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
        generate_root_cert('LioKor Proxy CA', ROOT_CA_CRT, ROOT_CA_KEY, ROOT_CERT_KEY)

    if not Path(CERTS_PATH).exists():
        os.makedirs(CERTS_PATH)

    serv = socket.create_server((host, port))
    serv.listen(32)
    print('Proxy serving at {}:{}'.format(host, port))
    while True:
        sock, addr = serv.accept()
        print('Connection from {}'.format(addr))
        thread = Thread(target=handle_connection, args=(sock, addr, ))
        thread.start()


if __name__ == '__main__':
    main()
