from email.parser import BytesParser

RECV_SIZE = 4096
CONNECTION_ESTABLISHED_RESPONSE = b'HTTP/1.1 200 Connection Established\r\n\r\n'


class HttpPacket:
    start_line: str
    headers: dict
    body: bytes

    def __init__(self, start_line: str, headers: dict, body: bytes):
        self.start_line = start_line
        self.headers = headers
        self.body = body

    def encode(self):
        return self.start_line.encode() + b'\r\n' + encode_headers(self.headers) + b'\r\n\r\n' + self.body


def encode_headers(headers: dict) -> bytes:
    headers_str = ''
    for key in headers:
        headers_str += '{}: {}\r\n'.format(key, headers[key])
    headers_str = headers_str[:len(headers_str) - 2]  # removing excess \r\n

    return headers_str.encode()


def receive_http(sock) -> HttpPacket:
    raw_http = b''
    while raw_http.find(b'\r\n\r\n') == -1:
        chunk = sock.recv(RECV_SIZE)
        raw_http += chunk

    head, body = raw_http.split(b'\r\n\r\n', 1)
    start_line, headers = head.split(b'\r\n', 1)
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

    return HttpPacket(start_line.decode(), dict(headers), body)
