#!/usr/bin/python3

# A simple server which echoes back anything you type.

import socket
import time

import tdtelnet

class EchoServer:
    host = ''
    port = 8211

    def __init__(self):
        self.server_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)

        self.connection_manager = tdtelnet.ConnectionManager(self.server_socket)

        # We don't need to do anything special for connection or
        # disconnection, so we don't assign handlers for those
        # events. Just for receiving messages:
        self.connection_manager.event_message = self.handle_message

    def handle_message(self, connection, message):
        # Echo the client's message back to them, with a newline
        connection.write(message + '\r\n')

    def run(self):
        print(f'Listening on {self.host}:{self.port}...')
        while True:
            time.sleep(0.1)
            self.connection_manager.update()

if __name__ == '__main__':
    server = EchoServer()
    server.run()
