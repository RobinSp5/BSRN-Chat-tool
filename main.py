import toml         # Zum Einlesen der Konfigurationsdatei (config.toml)
import threading    # Um mehrere Dinge gleichzeitig auszuführen (z. B. Server, CLI, Discovery)
import queue        # Für die Kommunikation zwischen den Modulen (Nachrichtenwarteschlangen)
import socket       # Für Netzwerkverbindungen über UDP

# Eigene Module einbinden
from cli import cli_loop, benutzername_abfragen_und_speichern, find_free_udp_port                      # Startet die Kommandozeile (Benutzereingabe)
from ipc_handler import ipc_handler           # Startet die zentrale Netzwerk-Kommunikation
from discovery import main as discovery_main

# === Hauptfunktion: Startet alle Programmteile ===
def main():
    print("🚀 SLCP Chat wird gestartet...")
    
    # --- 1) Nach Benutzername fragen und Konfiguration laden/speichern ---
    config = benutzername_abfragen_und_speichern()
    
    if not config.get("handle"):
        print("❌ Kein gültiger Name konfiguriert. Programm wird beendet.")
        return

    print(f"✅ Willkommen, {config['handle']}!")

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

    # --- 5) Discovery-Dienst im Hintergrund starten ---
    threading.Thread(
        target=discovery_main, 
        args=(discovery_port, config['handle'], peer_port), 
        daemon=True
    ).start()

    # --- 6) IPC-Handler starten (zentraler Netzwerkdienst: Empfangen, Senden, Discovery) ---
    threading.Thread(target=ipc_handler, args=(to_network, from_network, to_discovery, config), daemon=True).start()

    # --- 7) CLI starten (Benutzereingaben & Anzeige) ---
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
