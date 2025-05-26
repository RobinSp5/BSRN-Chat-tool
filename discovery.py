import socket
import threading
import toml
import sys

CONFIG_PATH = "config.toml"

try:
    config = toml.load(CONFIG_PATH)
    HANDLE = config["handle"]
    PORT = config["port"]
    WHOISPORT = config["whoisport"]
except Exception as e:
    print(f"Fehler beim Laden der Konfiguration: {e}")
    sys.exit(1)

users = {}  # {handle: (ip, port)}

def slcp_join():
    return f"JOIN {HANDLE} {PORT}"

def slcp_leave():
    return f"LEAVE {HANDLE}"

def slcp_who():
    return "WHO"

def handle_message(message, addr, sock):
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
        antwort = "KNOWUSERS " + ", ".join(f"{h} {ip} {p}" for h, (ip, p) in users.items())
        sock.sendto(antwort.encode("utf-8"), addr)
        print(f"[WHO] Antwort gesendet an {addr[0]}:{addr[1]}")

def listen_for_messages(sock):
    """Empfängt dauerhaft UDP-Nachrichten und leitet sie zur Verarbeitung weiter"""
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            message = data.decode()
            print(f"[Discovery] Nachricht von {addr}: {message}")
            handle_message(message, addr, sock)
        except Exception as e:
            print(f"[Fehler beim Empfangen]: {e}")

def sende_join_broadcast(handle, port, whoisport):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    msg = f"JOIN {handle} {port}"
    sock.sendto(msg.encode(), ('<broadcast>', whoisport))
    sock.close()

def main():
    """Discovery-Dienst: Empfängt JOIN, LEAVE, WHO und antwortet darauf."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', WHOISPORT))
    listen_for_messages(sock)

    # Nach dem Laden der Konfiguration:
    sende_join_broadcast(config["handle"], config["port"], config["whoisport"])

if __name__ == "__main__":
    main()
