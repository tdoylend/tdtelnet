#!/usr/bin/python3

import time
import socket
from collections import deque

class Connection:
    # Represents a connection from a client.
    # You should not instantiate this class yourself; instances of it
    # will be created as needed by the ConnectionManager when new clients connect.

    def __init__(self, id, sock, peer_addr):
        self.id = id                     # A unique number identifying this Connection.
        self.connected  = True           # Whether this connection is connected.
        
        self.fd = sock.fileno()         # The file descriptor (int) of the underlying socket.

        self.client_host = peer_addr[0] # The IP address/hostname of the client.
        self.client_port = peer_addr[1] # The port on the client machine that they are using to connect.

        self.max_line = 8192    # The maximum amount of text the client may send in a single line.
                                # This is not a hard maximum; it's intended to prevent malicious
                                # clients from filling your server's memory.

        self.timeout  = 300     # The number of seconds the client may go without sending a line.
                                # Set to 0 to disable the timeout.



        # These are internal. Don't modify/access them from outside.

        self.last_activity = time.time()

        self.sock = sock    # The socket which this Connection wraps.
        self.out_queue = b'' # outgoing data
        self.current_line = bytearray() # the line 'under construction'
        self.mode = 'normal'
        self.disp = 0

        self.pending_disconnect = None

    def write(self,msg):
        # Write some data to the client. Keep in mind that Telnet uses \r\n for
        # newlines, not \n.
        self.out_queue += msg.encode('utf-8')

    def write_raw(self,msg):
        # The same as write( ), but accepts a `bytes` object instead of a `str`.
        self.out_queue += msg

    def disconnect(self, reason):
        # Cause this connection to disconnect. At some point after calling this function,
        # you will receive an event_disconnection, *unless* the Connection has already been
        # previously disconnected; in that case, this function is a no-op.
        # 
        # `reason` should be a string.
        #
        if (not self.connected) or (self.pending_disconnect):
            return
        self.pending_disconnect = str(reason)
 
    
class ConnectionManager:
    def default_event_new_connection(self, connection):
        print(f'New connection #{connection.id} from {connection.client_host}:{connection.client_port}')

    def default_event_disconnection(self,connection, reason):
        print(f'Connection #{connection.id} closed. Reason: {reason}')

    def default_event_message(self, connection, message):
        print(f'Received from #{connection.id}: {message}')

    def default_event_parameter(self, connection, parameter, disposition):
        print(f'Connection #{connection.id} sent a Telnet control sequence: {disposition} {parameter}')

    def __init__(self, server_socket):
        self.active_connections = deque()

        self.server_socket = server_socket

        # Set these to your own event-handler functions.
        self.event_new_connection = self.default_event_new_connection
        self.event_message        = self.default_event_message
        self.event_disconnection  = self.default_event_disconnection
        self.event_parameter      = self.default_event_parameter

        self.server_socket.setblocking(0)

        self.global_id_counter = 0

    def update(self):
        # Updates all the managed connections and accepts new ones. Call this once per frame.
        try:
            sock, addr = self.server_socket.accept()
            sock.setblocking(0)
            self.global_id_counter += 1
            conn = Connection(self.global_id_counter,sock,addr)
            self.active_connections.append(conn)
            self.event_new_connection(conn)
        except BlockingIOError:
            pass

        for _ in range(len(self.active_connections)):
            connection = self.active_connections.popleft()

            try:
                if connection.out_queue:
                    num_bytes_sent = connection.sock.send(connection.out_queue)
                    #if not num_bytes_sent:
                    #    connection.disconnect('zero write')
                    connection.out_queue = connection.out_queue[num_bytes_sent:]
            except BlockingIOError:
                pass
            except IOError as e:
                connection.disconnect(str(e))
            
            if connection.timeout:
                if (time.time() - connection.last_activity) > connection.timeout:
                    connection.disconnect('timed out') 

            if len(connection.current_line) > connection.max_line:
                connection.disconnect('maximum line size exceeded')

            if connection.pending_disconnect is not None:
                connection.connected = False
                self.event_disconnection(connection, connection.pending_disconnect)
                try:
                    connection.sock.shutdown(socket.SHUT_RDWR)
                    connection.sock.close()
                except IOError: pass
                continue

            bytes_received = b''
            try:
                bytes_received = connection.sock.recv(4096)
                if not bytes_received:
                    connection.disconnect('disconnected')
            except BlockingIOError:
                pass
            except IOError as e:
                connection.disconnect(str(e))
            
            if connection.pending_disconnect is None:
                for byte in bytes_received:
                    if connection.mode == 'normal':
                        if byte == 255:
                            # Start Telnet control sequence
                            connection.mode = 'disposition'
                        elif byte == 8:
                            # Backspace
                            if connection.current_line: del connection.current_line[-1]
                        elif byte == 13:
                            # CR
                            # ignore
                            pass
                        elif byte == 10:
                            connection.last_activity = time.time()
                            self.event_message(
                                connection,
                                connection.current_line.decode('utf-8','replace')
                            )
                            connection.current_line.clear()
                            # The event handler may have caused a disconnect, in which
                            # case, stop parsing input.
                            if connection.pending_disconnect is not None:
                                break
                        else:
                            connection.current_line.append(byte)
                    elif connection.mode == 'disposition':
                        connection.disp = byte
                        connection.mode = 'parameter'
                    elif connection.mode == 'parameter':
                        connection.mode = 'normal'
                        self.event_parameter(connection,byte,connection.disp)
                        # Again, this may have caused a disconnect.
                        if connection.pending_disconnect is not None:
                            break
                    else:
                        raise ValueError(f'Invalid mode in Telnet parsing: {self.mode}')

            self.active_connections.append(connection)

if __name__ == '__main__':
    server_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    server_socket.bind(('localhost',9999))
    server_socket.listen(5)

    manager = ConnectionManager(server_socket)

    while True:
        manager.update()
        time.sleep(0.5)

