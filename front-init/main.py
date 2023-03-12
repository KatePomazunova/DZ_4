from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import mimetypes
import pathlib
import socket 
import logging
import json
from threading import Thread
import datetime

BUFFER_SIZE = 1024
SERVER_PORT = 5015
SERVER_HOST = "127.0.0.1"


class HttpHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        data = self.rfile.read(int(self.headers['Content-Length']))
        send_data_to_socket(data)

        self.send_response(302) 
        self.send_header('Location', '/message')
        self.end_headers()

    def do_GET(self):
        pr_url = urllib.parse.urlparse(self.path)
        if pr_url.path == '/':
            self.send_html_file('index.html')
        elif pr_url.path == '/message':
            self.send_html_file('message.html')
        else:
            if pathlib.Path().joinpath(pr_url.path[1:]).exists():
                self.send_static()
            else:
                self.send_html_file('error.html', 404)


    def send_html_file(self, filename, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as fd:
            self.wfile.write(fd.read())

    
    def send_static(self):
        self.send_response(200)
        mt = mimetypes.guess_type(self.path)
        if mt:
            self.send_header("Content-type", mt[0])
        else:
            self.send_header("Content-type", 'text/plain')
        self.end_headers()
        with open(f'.{self.path}', 'rb') as file:
            self.wfile.write(file.read())


def send_data_to_socket(data):
    c_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    c_socket.sendto(data, (SERVER_HOST, SERVER_PORT))
    c_socket.close()


def run_http_server(server_class=HTTPServer, handler_class=HttpHandler):
    server_address = (SERVER_HOST, 3015)
    http = server_class(server_address, handler_class)
    try:
        http.serve_forever()
    except KeyboardInterrupt:
        logging.info("Socket server stopped")
    finally:
        http.server_close()


def save_data_from_http_server(data):
    print(data)
    data_parse = urllib.parse.unquote_plus(data.decode())
   
    try:
        data_dict = {key: value for key, value in [el.split('=') for el in data_parse.split('&')]}
        
        with open(pathlib.Path("storage/data.json", "r", encoding="utf-8")) as json_file:
            dict_from_file = json.load(json_file)

        dict_from_file[str(datetime.datetime.now())] = data_dict

        with open(pathlib.Path("storage/data.json"), "w", encoding="utf-8") as fd:
            json.dump(dict_from_file, fd, ensure_ascii=False, indent=4)

    except ValueError as err:
        logging.debug(f'for data {data_parse} error {err}')
    except OSError as err:
        logging.debug(f'Write data {data_parse} error {err}')
      

def run_socket_server(host, port):
    s_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s_socket.bind((host, port))

    try:
        while True:
            msg, address = s_socket.recvfrom(BUFFER_SIZE)
            save_data_from_http_server(msg)
    except KeyboardInterrupt:
        logging.info("Socket server stopped")
    finally:
        s_socket.close()
       


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format="%(threadName)s %(message)s")
    STORAGE_DIR = pathlib.Path().joinpath('storage')
    FILE_STORAGE = STORAGE_DIR / 'data.json'
    if not FILE_STORAGE.exists():
        with open(FILE_STORAGE, 'w', encoding='utf-8') as fd:
            json.dump({}, fd, ensure_ascii=False, indent=4)

    th_server = Thread(target=run_http_server)
    th_server.start()
    th_socket = Thread(target=run_socket_server(SERVER_HOST, SERVER_PORT))
    th_socket.start()
