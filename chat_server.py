#!/usr/bin/python3

# A simple example chat server.

import socket
import time

import tdtelnet

ALLOWED_USERNAME_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.!?$%*_-=+^&#~|@'

class ChatServer:
    host = ''
    port = 8212

    def __init__(self):
        # Create the server socket.
        self.server_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.server_socket.bind((self.host,self.port))
        self.server_socket.listen(5)

        # Initialize the ConnectionManager.
        self.connection_manager = tdtelnet.ConnectionManager(self.server_socket)

        # Set the handlers for various events.
        self.connection_manager.event_new_connection = self.handle_new_connection
        self.connection_manager.event_disconnection  = self.handle_disconnection
        self.connection_manager.event_message        = self.handle_message

        
        self.usernames = {} # maps connection IDs to usernames
        self.states = {}    # gives the state of each connection

    def handle_new_connection(self,connection):
        print(f'New connection #{connection.id} from {connection.client_host}:{connection.client_port}')

        self.states[connection.id] = 'waiting-for-username'
        connection.write('Please enter a username: ')

    def handle_disconnection(self,connection,reason):
        if connection.id in self.usernames:
            print(f'Disconnected #{connection.id} ({self.usernames[connection.id]}) -> {reason}')
        else:    
            print(f'Disconnected #{connection.id} -> {reason}')

        if connection.id in self.usernames:
            self.announce(connection.id, self.usernames[connection.id] + ' has left the chat.')
            del self.usernames[connection.id]

    def handle_message(self,connection, msg):
        if self.states[connection.id] == 'waiting-for-username':
            if msg in self.usernames.values():
                connection.write('That username is already taken.\r\nPlease try again: ')
                return
            elif len(msg) > 16:
                connection.write('Username too long.\r\nPlease try again: ')
                return
            elif any(map(lambda x: x not in ALLOWED_USERNAME_CHARS, msg)):
                connection.write('Username contains invalid characters.\r\nPlease try again: ')
                return

            if self.usernames:
                connection.write('Presently connected: {}\r\n'.format(', '.join(self.usernames.values())))
            else:
                connection.write('There is no one else here at the moment.\r\n')
            
            self.usernames[connection.id] = msg
            self.states[connection.id] = 'chatting'

            connection.timeout = 0 # disable timeouts for chatters

            self.announce(connection.id, self.usernames[connection.id] + ' has joined the chat.')

        elif self.states[connection.id] == 'chatting':
            self.announce(connection.id,'<'+self.usernames[connection.id] + '> ' + msg)
            print(f'{connection.id} ({self.usernames[connection.id]}): {msg}')
        else:
            raise ValueError(f'invalid connection state: {self.states[connection.id]}')
            

    def announce(self,speaker,message):
        # Speaker is the connection ID of the person making the announcement.
        # We don't send the person's own message to themself.

        for connection in self.connection_manager.active_connections:
            if connection.id in self.usernames: # don't announce to losers who aren't logged in
                if connection.id != speaker:
                    connection.write(message+'\r\n')

    def run(self):
        while True:
            time.sleep(0.1)
            self.connection_manager.update()


if __name__ == '__main__':
    chat_server = ChatServer()

    print(f'Serving on {chat_server.host}:{chat_server.port}')

    chat_server.run()
