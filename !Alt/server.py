import socket

def start_server(listen_port=5001):
    """
    Startet einen UDP-Server, der auf dem angegebenen Port auf Nachrichten wartet.
    Jede empfangene Nachricht wird mit Absenderadresse auf der Konsole ausgegeben.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP-Socket erstellen
    sock.bind(('', listen_port))  # An allen Interfaces auf listen_port binden
    print(f"Empfange Nachrichten auf Port {listen_port}...")

    while True:
        # Auf eingehende Nachrichten warten (blockierend)
        data, addr = sock.recvfrom(1024)
        # Nachricht und Absenderadresse ausgeben
        print(f"Nachricht von {addr}: {data.decode()}")
