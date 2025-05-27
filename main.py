import toml         # Zum Einlesen der Konfigurationsdatei (config.toml)
import threading    # Um mehrere Dinge gleichzeitig auszuführen (z. B. Server, CLI, Discovery)
import queue        # Für die Kommunikation zwischen den Modulen (Nachrichtenwarteschlangen)
import socket       # Für Netzwerkverbindungen über UDP

# Eigene Module einbinden
from cli import cli_loop                      # Startet die Kommandozeile (Benutzereingabe)
from ipc_handler import ipc_handler           # Startet die zentrale Netzwerk-Kommunikation

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
    from_network = queue.Queue()  # Vom Netzwerk an CLI (Empfang)
    to_discovery = queue.Queue()  # Von CLI an Discovery

    # --- 5) IPC-Handler starten (zentraler Netzwerkdienst: Empfangen, Senden, Discovery) ---
    threading.Thread(target=ipc_handler, args=(to_network, from_network, to_discovery, config), daemon=True).start()

    # --- 6) CLI starten (Benutzereingaben & Anzeige) ---
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
