import selectors
import socket
import sys
import types

sel = selectors.DefaultSelector()


host, port = sys.argv[1], int(sys.argv[2])
lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
lsock.bind((host, port))
lsock.listen()
print(f"Listening on {(host, port)}")
lsock.setblocking(False)
sel.register(lsock, selectors.EVENT_READ, data=None)


def accept_wrapper(sock):
    """
    Accepts a new client connecito on a given listening socket, configures the conneciton to be non-blocking, and registers it with the selectors
    for handling both read and write events.

    parameters:
    sock (socket.socket): The server socket that is ready aceept a new client connection.

    Side Effects:
    - Acccepts a client connection and retireves the client's address.
    - Sets the accepted connection to non-blocking mode to handle I/O asynchronously.
    - Registers the connection with the selector to monitor both read and write events.

    Attributes:
    - conn (socket.socket): The accepted client connection socket.
    - addr (tuple): The client's IP address and port.
    - data (types.SimpleNamespace): A namespace to hold the client address, incoming data buffer (inb), and outgoing data buffer (outb)


    Returns:
    None

    """
    conn, addr = sock.accept()
    print(f"Accepted connection from {addr}")
    conn.setblocking(False)
    data = types.SimpleNamespace(add=addr, inb=b"", outb=b"")
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    sel.register(conn, events, data=data)


def service_connection(key, mask):
    """
    Handles read and write events on a connected client socket based on the given
    event mask. If there is data to read, it appends it to the outgoing buffer to be
    echoed back to the client. If there is data to write, it sends it to the client.

    Parameters:
    key (selectors.SelectorKey): A key object that contains the file object (socket)
                                 and any associated data for the registered event.
    mask (int): An event mask indicating which events (read, write) are ready.

    Behavior:
    - If the socket is ready for reading, it reads up to 1024 bytes of data.
      - If data is received, it appends this data to `data.outb` for later writing.
      - If no data is received, it indicates the client has closed the connection,
        so the socket is unregistered from the selector and closed.
    - If the socket is ready for writing, it checks `data.outb` for any outgoing data.
      - If there is data, it sends it to the client and removes the sent bytes
        from `data.outb`.

    Attributes:
    - sock (socket.socket): The client socket associated with this key.
    - data (types.SimpleNamespace): Holds `addr` (client's address) and buffers
      for incoming (`inb`) and outgoing (`outb`) data.

    Returns:
    None
    """
    sock = key.fileobj
    data = key.data
    if mask & selectors.EVENT_READ:
        recv_data = sock.recv(1024)  # Should be ready to read
        if recv_data:
            data.outb += recv_data
        else:
            print(f"Closing connection to {data.addr}")
            sel.unregister(sock)
            sock.close()
    if mask & selectors.EVENT_WRITE:
        if data.outb:
            print(f"Echoing {data.outb!r} to {data.addr}")
            sent = sock.send(data.outb)  # Should be ready to write
            data.outb = data.outb[sent:]


try:
    while True:
        events = sel.select(timeout=None)
        for key, mask in events:
            if key.data is None:
                accept_wrapper(key.fileobj)
            else:
                service_connection(key, mask)
except KeyboardInterrupt:
    print("Caught keyboard interrupt, existing")
finally:
    sel.close()
