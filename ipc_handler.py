import threading
import queue
import socket

# SLCP-Nachricht parsen
def parse_slcp(msg: str):
    parts = msg.strip().split(" ", 2)
    if len(parts) >= 2:
        return {
            "command": parts[0],
            "handle": parts[1],
            "text": parts[2] if len(parts) > 2 else ""
        }
    else:
        return {
            "command": parts[0],
            "raw": msg
        }

def ipc_handler(to_network, from_network, to_discovery, config):
    """
    Vermittelt Nachrichten zwischen den Queues und verarbeitet sie.
    Startet UDP-Empfang, Sende-Logik und Discovery-Bridge.
    """

    recv_port = config.get("serverport", config.get("port", 5001))  # Empfangsport für Nachrichten
    send_port = config.get("port", 5000)                            # Sendeport (eigene Adresse)
    discovery_port = config.get("whoisport", 4000)                  # Discovery-Port

    handle = config.get("handle", "Unbekannt")

    # === Empfangssocket (nur lesen) ===
    recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    recv_sock.bind(('', recv_port))

    # === Broadcast-Socket für Senden ===
    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    send_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    def empfangen():
        while True:
            try:
                data, addr = recv_sock.recvfrom(4096)
                message = data.decode("utf-8", errors="ignore")
                print(f"[Empfangen] {addr}: {message}")
                parsed = parse_slcp(message)
                from_network.put(message)
            except Exception as e:
                print(f"[Fehler beim Empfang]: {e}")

    def senden():
        while True:
            try:
                item = to_network.get(timeout=1)
                if isinstance(item, tuple) and len(item) == 3:
                    typ, ziel, inhalt = item
                    if typ in ["MSG", "LEAVE", "JOIN"]:
                        send_sock.sendto(inhalt.encode(), ziel)
                    elif typ == "IMG" and isinstance(inhalt, tuple):
                        header, bilddaten = inhalt
                        send_sock.sendto(header.encode(), ziel)
                        send_sock.sendto(bilddaten, ziel)
                elif isinstance(item, str):
                    parts = item.split(" ", 2)
                    if len(parts) >= 3 and parts[1] == "Broadcast":
                        msg = f"{parts[0]} {handle} {parts[2]}"
                        send_sock.sendto(msg.encode(), ('<broadcast>', recv_port))
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[Fehler beim Senden]: {e}")

    def discovery_listener():
        discovery_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        discovery_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        while True:
            try:
                command = to_discovery.get(timeout=1)
                discovery_sock.sendto(command.encode(), ('<broadcast>', discovery_port))
                print(f"[Discovery] gesendet: {command}")
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[Discovery Fehler]: {e}")

    # Threads starten
    threading.Thread(target=empfangen, daemon=True).start()
    threading.Thread(target=senden, daemon=True).start()
    threading.Thread(target=discovery_listener, daemon=True).start()
