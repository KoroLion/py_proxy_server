import socket
from threading import Thread

from email.parser import BytesParser
from urllib.parse import urlparse


HOST = '127.0.0.1'
PORT = 8000
RECV_SIZE = 4096


def encode_headers(headers: str):
    if headers.find('\r\n') == -1:
        headers = headers.replace('\n', '\r\n')
    return headers.encode()


def receive_http(sock):
    raw_http = b''
    while raw_http.find(b'\r\n\r\n') == -1:
        chunk = sock.recv(RECV_SIZE)
        raw_http += chunk

    head, body = raw_http.split(b'\r\n\r\n', 1)
    first_line, headers = head.split(b'\r\n', 1)
    headers = BytesParser().parsebytes(headers)

    if headers.get('Content-Length', None):
        length = int(headers['Content-Length'])
        while len(body) < length:
            body += sock.recv(4096)
    elif headers.get('Transfer-Encoding', None) == 'chunked':
        while body.find(b'\r\n0\r\n') == -1:
            chunk = sock.recv(4096)
            body += chunk
        if body.endswith(b'0\r\n'):
            body += b'\r\n'
        if body.endswith(b'0\r\n\r'):
            body += b'\n'

    return first_line, headers, body


def handle_connection(client_sock, addr):
    request, headers, body = receive_http(client_sock)

    method, url, protocol = request.split(b' ', 2)
    if method == b'CONNECT':
        client_sock.sendall(b'HTTP/1.1 200 Connection Established\r\n\r\n')
        client_sock.close()
        return

    del headers['Proxy-Connection']

    url = urlparse(url)
    port = 80 if url.port is None else url.port

    new_request = b' '.join([method, url.path, protocol])
    new_headers = encode_headers(headers.as_string())

    new_request = new_request + b'\r\n' + new_headers + body
    print(new_request)

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.connect((url.hostname, port))
    server_sock.sendall(new_request)

    response, headers, body = receive_http(server_sock)

    server_sock.close()

    headers = encode_headers(headers.as_string())
    new_response = response + b'\r\n' + headers + body

    client_sock.sendall(new_response)
    client_sock.close()


serv = socket.create_server((HOST, PORT))
serv.listen(32)
print('Proxy serving at {}:{}'.format(HOST, PORT))
while True:
    sock, addr = serv.accept()
    print('Connection from {}'.format(addr))
    thread = Thread(target=handle_connection, args=(sock, addr, ))
    thread.start()
