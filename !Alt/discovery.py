import socket
import threading
import toml
import sys

users = {}  # {handle: (ip, port)}

def handle_message(message, addr, sock):
    """Verarbeitet eingehende Discovery-Nachrichten"""
    teile = message.strip().split()
    if not teile:
        return

    befehl = teile[0]

    if befehl == "JOIN" and len(teile) == 3:
        handle = teile[1]
        port = int(teile[2])
        users[handle] = (addr[0], port)
        print(f"[JOIN] {handle} ist beigetreten von {addr[0]}:{port}")

    elif befehl == "LEAVE" and len(teile) == 2:
        handle = teile[1]
        if handle in users:
            del users[handle]
            print(f"[LEAVE] {handle} hat den Chat verlassen")

    elif befehl == "WHO":
        if users:
            # Antwort mit allen bekannten Benutzern
            antwort = "KNOWUSERS " + ", ".join(f"{h} {ip} {p}" for h, (ip, p) in users.items())
        else:
            antwort = "KNOWUSERS"
        sock.sendto(antwort.encode("utf-8"), addr)
        print(f"[WHO] Antwort gesendet an {addr[0]}:{addr[1]}: {antwort}")

def listen_for_messages(sock):
    """Empfängt dauerhaft UDP-Nachrichten und leitet sie zur Verarbeitung weiter"""
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            message = data.decode()
            print(f"[Discovery] Nachricht von {addr}: {message}")
            handle_message(message, addr, sock)
        except Exception as e:
            print(f"[Discovery Fehler]: {e}")

def sende_join_broadcast(handle, port, whoisport):
    """Sendet JOIN-Broadcast beim Start"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    msg = f"JOIN {handle} {port}"
    sock.sendto(msg.encode(), ('<broadcast>', whoisport))
    sock.close()
    print(f"[Discovery] JOIN-Broadcast gesendet: {msg}")

def main(discovery_port=4000, handle="Unknown", port=5000):
    """Discovery-Dienst: Empfängt JOIN, LEAVE, WHO und antwortet darauf."""
    print(f"[Discovery] Starte Discovery-Dienst auf Port {discovery_port}")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', discovery_port))
    
    # Eigenen JOIN senden
    sende_join_broadcast(handle, port, discovery_port)
    
    # Auf Nachrichten hören
    listen_for_messages(sock)

if __name__ == "__main__":
    # Nur für direkten Test
    try:
        config = toml.load("config.toml")
        main(config.get("whoisport", 4000), config.get("handle", "Test"), config.get("port", 5000))
    except Exception as e:
        print(f"Fehler: {e}")
        main()
