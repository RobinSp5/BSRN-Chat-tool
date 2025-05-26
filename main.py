import toml         # Zum Einlesen der Konfigurationsdatei (config.toml)
import threading    # Um mehrere Dinge gleichzeitig auszuführen (z. B. Server, CLI, Discovery)
import queue        # Für die Kommunikation zwischen den Modulen (Nachrichtenwarteschlangen)
import socket       # Für Netzwerkverbindungen über UDP

# Eigene Module einbinden
from discovery import main as discovery_main  # Startet den Discovery-Dienst (JOIN, WHO, LEAVE)
from server import start_server               # Startet den Nachrichtenspeicher (Server-Empfänger)
from cli import cli_loop                      # Startet die Kommandozeile (Benutzereingabe)

# === Hilfsfunktion: Freien Port finden ===
def find_free_udp_port(start_port: int) -> int:
    """
    Sucht ab einem gegebenen Startport den nächsten freien UDP-Port.
    Wichtig, falls Standardports bereits belegt sind.
    """
    port = start_port
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            try:
                s.bind(('', port))  # Wenn erfolgreich, Port ist frei
                return port
            except OSError:
                port += 1  # Sonst nächsten Port versuchen

# === Bridge-Funktion: WHO aus der CLI ins Netzwerk senden ===
def bridge_discovery_queue(to_discovery, discovery_port):
    """
    Wartet auf WHO-Befehle in der CLI-Queue und sendet diese per UDP-Broadcast.
    So können Nutzer im Netzwerk gefunden werden.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    while True:
        try:
            command = to_discovery.get(timeout=1)
            if command == "WHO":
                # WHO-Befehl senden an alle im lokalen Netzwerk
                sock.sendto("WHO".encode(), ('<broadcast>', discovery_port))
                print("🔍 WHO-Anfrage gesendet...")
        except queue.Empty:
            continue  # Wenn nichts da ist → einfach weiter warten
        except Exception as e:
            print(f"❌ Fehler beim Discovery-Bridge: {e}")

# === Hauptfunktion: Startet alle Programmteile ===
def main():
    # --- 1) Konfiguration aus Datei laden ---
    try:
        config = toml.load("config.toml")  # TOML-Datei mit Benutzernamen, Ports usw.
        print("✅ Konfiguration geladen aus config.toml")
    except Exception as e:
        print(f"❌ Fehler beim Laden der Konfiguration: {e}")
        return  # Ohne Konfiguration kein Start

    # --- 2) Ports aus der Konfiguration holen oder Standardwerte setzen ---
    peer_port      = config.get("port", 5000)
    discovery_port = config.get("whoisport", peer_port)
    server_port    = config.get("serverport", peer_port + 1)

    # --- 3) Prüfen, ob Ports frei sind ---
    discovery_port = find_free_udp_port(discovery_port)
    server_port    = find_free_udp_port(server_port)

    print(f"🔍 Discovery läuft auf UDP-Port {discovery_port}")
    print(f"🖥️ Server hört auf UDP-Port {server_port}")

    # --- 4) Queues für Kommunikation zwischen den Komponenten ---
    to_network   = queue.Queue()  # Von CLI an den Netzwerk-Sender
    from_network = queue.Queue()  # Vom Server an CLI (Empfang)
    to_discovery = queue.Queue()  # Von CLI an Discovery-Bridge (z. B. WHO)

    # --- 5) Discovery-Dienst starten (für JOIN, LEAVE, WHO empfangen) ---
    threading.Thread(target=discovery_main, daemon=True).start()

    # --- 6) Discovery-Bridge starten (damit WHO aus der CLI im Netzwerk landet) ---
    threading.Thread(target=bridge_discovery_queue, args=(to_discovery, discovery_port), daemon=True).start()

    # --- 7) Nachrichtenserver starten (zum Empfang von MSG, IMG etc.) ---
    threading.Thread(target=start_server, args=(server_port,), daemon=True).start()

    # --- 8) CLI starten (Benutzereingaben & Anzeige) ---
    print("💬 Starte CLI. Mit /help bekommst du alle Befehle.")
    try:
        cli_loop(to_network, from_network, to_discovery)
    except KeyboardInterrupt:
        print("\n👋 CLI beendet durch Benutzer.")
    except Exception as e:
        print(f"❌ Fehler in der CLI: {e}")

# === Einstiegspunkt: Wenn Datei direkt ausgeführt wird ===
if __name__ == "__main__":
    main()
