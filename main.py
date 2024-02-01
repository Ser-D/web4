import json
import logging
import mimetypes
import os
import pathlib
import socket
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
from threading import Thread

BASE_DIR = pathlib.Path()
UDP_IP = '127.0.0.1'
UDP_PORT = 5000
SERVER_IP = '0.0.0.0'
SERVER_PORT = 3000
BUFFER = 1024


def send_data_to_socket(body):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.sendto(body, (UDP_IP, UDP_PORT))
    client_socket.close()


class HttpHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        pr_url = urllib.parse.urlparse(self.path)
        if pr_url.path == '/':
            self.send_html_file('index.html')
        elif pr_url.path == '/message.html':
            self.send_html_file('message.html')
        else:
            file = BASE_DIR.joinpath(pr_url.path[1:])
            if file.exists():
                self.send_static(file)
            else:
                self.send_html_file('error.html', 404)

    def send_html_file(self, filename, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as fd:
            self.wfile.write(fd.read())

    def send_static(self, filename, status=200):
        self.send_response(status)
        mt, *_ = mimetypes.guess_type(self.path)
        if mt:
            self.send_header('Content-type', mt)
        else:
            self.send_header('Content-type', 'text/plain')
        self.end_headers()
        with open(filename, 'rb') as fl:
            self.wfile.write(fl.read())

    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        send_data_to_socket(body)
        self.send_response(302)
        self.send_header("Location", "/message")
        self.end_headers()


def save_data_from_socket(data):
    body = urllib.parse.unquote_plus(data.decode())
    filename = BASE_DIR.joinpath('storage/data.json')
    payload = {key: value for key, value in [el.split("=") for el in body.split("&")]}
    current_date = datetime.now().strftime(format="%Y-%m-%d %H:%M:%S.%f")
    if os.path.exists(filename) and os.path.getsize(filename) != 0:
        try:
            try:
                with open(filename, "r+", encoding="utf-8") as json_file:
                    existing_data = json.load(json_file)
            except FileNotFoundError:
                existing_data = {}
            temp_data = {current_date: payload}
            existing_data.update(temp_data)
            with open(filename, "w+", encoding="utf-8") as json_file:
                json.dump(existing_data, json_file, indent=4, ensure_ascii=False)

        except ValueError as err:
            logging.error(f"Field parse data {body} with error {err}")
        except OSError as err:
            logging.error(f"Field write data {body} with error {err}")
    else:
        first_record = {current_date: payload}
        try:
            with open(
                filename,
                "w",
                encoding="utf-8",
            ) as json_file:
                json.dump(first_record, json_file, indent=4, ensure_ascii=False)
        except ValueError as err:
            logging.error(f"Field parse data {body} with error {err}")
        except OSError as err:
            logging.error(f"Field write data {body} with error {err}")


def http_server_run(server=HTTPServer, handler=HttpHandler):
    logging.info("Starting http server")
    server_address = (SERVER_IP, SERVER_PORT)
    http_server = server(server_address, handler)
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        http_server.server_close()


def socket_server_run(ip, port):
    logging.info("Starting socket server")
    socket_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server = ip, port
    socket_server.bind(server)
    try:
        while True:
            data, address = socket_server.recvfrom(BUFFER)
            save_data_from_socket(data)
    except KeyboardInterrupt:
        logging.info("Socked server stopped")
    finally:
        socket_server.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(threadName)s %(message)s')
    STORAGE_DIR = pathlib.Path().joinpath("storage")
    FILE_STORAGE = STORAGE_DIR / "data.json"
    if not FILE_STORAGE.exists():
        with open(FILE_STORAGE, "w", encoding="utf-8") as file:
            json.dump({}, file, ensure_ascii=False)
    thread_http = Thread(target=http_server_run)
    thread_http.start()
    thread_socket = Thread(target=socket_server_run(UDP_IP, UDP_PORT))
    thread_socket.start()
