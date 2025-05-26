import toml
import threading
import queue
import socket

from discovery import main as discovery_main
from server import start_server
from cli import cli_loop

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

def bridge_discovery_queue(to_discovery, discovery_port):
    """Bridge zwischen CLI-Queue und Discovery-Service"""
    import socket
    import time
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
    while True:
        try:
            command = to_discovery.get(timeout=1)
            if command == "WHO":
                # WHO-Broadcast senden
                sock.sendto("WHO".encode(), ('<broadcast>', discovery_port))
                print("🔍 WHO-Anfrage gesendet...")
        except queue.Empty:
            continue
        except Exception as e:
            print(f"❌ Fehler beim Discovery-Bridge: {e}")

def main():
    # 1) Konfiguration laden
    try:
        config = toml.load("config.toml")
        print("✅ Konfiguration geladen aus config.toml")
    except Exception as e:
        print(f"❌ Fehler beim Laden der Konfiguration: {e}")
        return

    # 2) Ports aus der Config oder Default-Werte
    peer_port      = config.get("port", 5000)
    discovery_port = config.get("whoisport", peer_port)
    server_port    = config.get("serverport", peer_port + 1)

    # 3) Freie Ports finden, falls schon belegt
    discovery_port = find_free_udp_port(discovery_port)
    server_port    = find_free_udp_port(server_port)

    print(f"🔍 Discovery läuft auf UDP-Port {discovery_port}")
    print(f"🖥️ Server hört auf UDP-Port {server_port}")

    # 4) Queues für Kommunikation erstellen
    to_network   = queue.Queue()
    from_network = queue.Queue()
    to_discovery = queue.Queue()

    # 5) Discovery in Background-Thread starten (NUR zum Empfangen)
    threading.Thread(target=discovery_main, daemon=True).start()

    # 6) Discovery-Bridge starten (für WHO-Befehle aus CLI)
    threading.Thread(target=bridge_discovery_queue, args=(to_discovery, discovery_port), daemon=True).start()

    # 7) Server in Background-Thread starten
    threading.Thread(target=start_server, args=(server_port,), daemon=True).start()

    # 8) CLI starten
    print("💬 Starte CLI. Mit /help bekommst du alle Befehle.")
    try:
        cli_loop(to_network, from_network, to_discovery)
    except KeyboardInterrupt:
        print("\n👋 CLI beendet durch Benutzer.")
    except Exception as e:
        print(f"❌ Fehler in der CLI: {e}")

if __name__ == "__main__":
    main()
