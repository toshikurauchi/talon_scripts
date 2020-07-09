import socket
import sys
import json


client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect(('localhost', 8324))

while True:
    try:
        data = client_socket.recv(1024)
        data = json.loads(data)
        print(data)
    except json.JSONDecodeError:
        pass
