import logging
import json
from urllib.parse import urlparse

from flask import Flask, Blueprint, current_app, request

from utils.file_utils import read_file
from utils.http_utils import send_request

requests_app = Blueprint('requests_app', __name__)


def create_flask_app():
    app = Flask(__name__)
    app.register_blueprint(requests_app)
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    return app


@requests_app.route('/api/requests/send', methods=['POST'])
def api_requests_send():
    data = json.loads(request.data)

    https = True if data['protocol'] == 'https' else False

    url = urlparse(data['url'])

    host = url.hostname
    port = url.port
    if not port:
        port = 443 if https else 80

    host_addr = (host, port)
    req = data['request'].encode()

    response = send_request(host_addr, req, https)

    return str(response)


@requests_app.route('/api/requests', methods=['GET'])
def api_requests_page():
    cur = current_app.config['con'].cursor()
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


@requests_app.route('/api/requests/<id>', methods=['GET'])
def api_request_page(id):
    cur = current_app.config['con'].cursor()
    cur.execute('SELECT id, time, protocol, method, url, request, response FROM requests WHERE id = ?', (int(id), ))
    data = cur.fetchall()
    request = {}
    if len(data) == 1:
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


@requests_app.route('/requests', methods=['GET'])
def requests_page():
    template = read_file('./templates/requests.html')
    return template


@requests_app.route('/requests/<id>', methods=['GET'])
def request_page(id):
    template = read_file('./templates/request.html')
    return template
