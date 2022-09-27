# tdtelnet

A tiny Telnet server library for Python.

File `tdtelnet.py` contains the library itself; the other scripts are examples. If you are
new to servers in general, start with `echo_server.py` and then example `chat_server.py` for
a simple but functional chat server.

Please note: this library only implements a *very* small portion of the Telnet spec. It
doesn't understand suboption negotiation at all, and it doesn't do any kind of processing
on incoming Telnet options -- it just passes them onto your program. If you want to do anything
fancy with Telnet, like detecting the window size automatically or supporting mouse input,
you'll need to extend this library significantly.

It's also not particularly efficient; it polls each socket individually, rather than using 
select( ) or epoll( ) en masse. Unless you are writing a server to support thousands and
thousands of clients, this is probably fine.
