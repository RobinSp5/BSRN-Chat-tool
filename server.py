import socket

def start_server(listen_port=5001):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', listen_port))
    print(f"Empfange Nachrichten auf Port {listen_port}...")

    while True:
        data, addr = sock.recvfrom(1024)
        print(f"Nachricht von {addr}: {data.decode()}")
