import toml
import threading
import queue
import socket

from cli import cli_loop
from discovery import main as discovery_main, sende_join_broadcast
from server import start_server

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

def find_free_udp_port(start_port: int) -> int:
    """Findet ab start_port den ersten freien UDP-Port."""
    port = start_port
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            try:
                s.bind(('', port))
                return port
            except OSError:
                port += 1

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

def network_sender(to_network, config):
    """Sendet Nachrichten aus der to_network Queue über das Netzwerk"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
    while True:
        try:
            message = to_network.get()
            if message.startswith("MSG"):
                # Format: "MSG Broadcast Hallo Welt" oder "MSG user123 Private Nachricht"
                parts = message.split(' ', 2)
                if len(parts) >= 3:
                    target = parts[1]
                    text = parts[2]
                    
                    if target == "Broadcast":
                        # Broadcast an alle
                        slcp_msg = f"MSG {config['handle']} {text}"
                        sock.sendto(slcp_msg.encode(), ('<broadcast>', config['port']))
                    else:
                        # Private Nachricht (hier vereinfacht als Broadcast)
                        slcp_msg = f"MSG {config['handle']} @{target} {text}"
                        sock.sendto(slcp_msg.encode(), ('<broadcast>', config['port']))
                        
            elif message.startswith("IMG"):
                # Bildnachricht
                parts = message.split(' ', 2)
                if len(parts) >= 3:
                    target = parts[1]
                    filepath = parts[2]
                    slcp_msg = f"IMG {config['handle']} {filepath}"
                    sock.sendto(slcp_msg.encode(), ('<broadcast>', config['port']))
                    
        except Exception as e:
            print(f"❌ Fehler beim Senden: {e}")

def discovery_bridge(to_discovery, config):
    """Bridge zwischen CLI-Discovery-Befehlen und UDP-Broadcasts"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
    while True:
        try:
            command = to_discovery.get()
            
            if command == "WHO":
                sock.sendto("WHO".encode(), ('<broadcast>', config['whoisport']))
                
            elif command.startswith("JOIN"):
                parts = command.split(' ', 2)
                if len(parts) >= 3:
                    handle = parts[1]
                    port = parts[2]
                    msg = f"JOIN {handle} {port}"
                    sock.sendto(msg.encode(), ('<broadcast>', config['whoisport']))
                    
            elif command.startswith("LEAVE"):
                parts = command.split(' ', 1)
                if len(parts) >= 2:
                    handle = parts[1]
                    msg = f"LEAVE {handle}"
                    sock.sendto(msg.encode(), ('<broadcast>', config['whoisport']))
                    
        except Exception as e:
            print(f"❌ Fehler bei Discovery-Bridge: {e}")

def main():
    # 1) Konfiguration laden
    try:
        config = toml.load("config.toml")
        print("✅ Konfiguration geladen aus config.toml")
    except Exception as e:
        print(f"❌ Fehler beim Laden der Konfiguration: {e}")
        return

    # 2) Ports setzen
    peer_port = config.get("port", 5000)
    discovery_port = config.get("whoisport", peer_port)
    server_port = config.get("serverport", peer_port + 1)

    # 3) Freie Ports finden
    discovery_port = find_free_udp_port(discovery_port)
    server_port = find_free_udp_port(server_port)
    peer_port = find_free_udp_port(peer_port)

    # Aktualisiere Config mit gefundenen Ports
    config["port"] = peer_port
    config["whoisport"] = discovery_port
    config["serverport"] = server_port

    print(f"🔍 Discovery läuft auf UDP-Port {discovery_port}")
    print(f"🖥️ Server hört auf UDP-Port {server_port}")
    print(f"📡 Chat-Port: {peer_port}")

    # 4) Queues erstellen
    to_network = queue.Queue()
    from_network = queue.Queue()
    to_discovery = queue.Queue()

    # 5) Discovery-Dienst starten
    threading.Thread(target=discovery_main, daemon=True).start()

    # 6) Netzwerk-Sender starten
    threading.Thread(target=network_sender, args=(to_network, config), daemon=True).start()

    # 7) Discovery-Bridge starten
    threading.Thread(target=discovery_bridge, args=(to_discovery, config), daemon=True).start()

    # 8) Server für eingehende Nachrichten starten
    threading.Thread(target=start_server, args=(server_port, from_network), daemon=True).start()

    # 9) JOIN-Broadcast beim Start senden
    sende_join_broadcast(config["handle"], config["port"], config["whoisport"])

    # 10) CLI starten
    print("💬 Starte CLI. Mit /help bekommst du alle Befehle.")
    print(f"💡 Du bist als '{config['handle']}' unterwegs")
    
    try:
        cli_loop(to_network, from_network, to_discovery)
    except KeyboardInterrupt:
        print("\n👋 CLI beendet durch Benutzer.")
        # LEAVE senden beim Beenden
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            leave_msg = f"LEAVE {config['handle']}"
            sock.sendto(leave_msg.encode(), ('<broadcast>', config['whoisport']))
            sock.close()
        except:
            pass
    except Exception as e:
        print(f"❌ Fehler in der CLI: {e}")

if __name__ == "__main__":
    main()
