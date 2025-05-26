import toml
import threading
import queue
from discovery import main as discovery_main
from server import start_server
from cli import cli_loop

def main():
    # --- 1) Konfiguration laden ---
    try:
        config = toml.load("config.toml")
        print("✅ Konfigurationsdatei geladen.")
    except FileNotFoundError:
        print("❌ Konfigurationsdatei nicht gefunden.")
        return
    except toml.TomlDecodeError:
        print("❌ Fehler beim Dekodieren der Konfigurationsdatei.")
        return

    # Flache Keys statt network-Tabelle
    peer_port    = config.get("port", 5000)
    discovery_port = config.get("whoisport", 4000)
    server_port  = peer_port + 1  # z.B. Port+1 für den Empfangs-Server

    # --- 2) Discovery-Service (Daemon-Thread) ---
    try:
        threading.Thread(target=discovery_main, daemon=True).start()
        print(f"🔍 Discovery-Dienst gestartet auf Port {discovery_port}.")
    except Exception as e:
        print(f"❌ Fehler beim Starten des Discovery-Dienstes: {e}")
        return

    # --- 3) Server (Daemon-Thread) ---
    try:
        threading.Thread(target=start_server, args=(server_port,), daemon=True).start()
        print(f"🖥️ Server gestartet und hört auf Port {server_port}.")
    except Exception as e:
        print(f"❌ Fehler beim Starten des Servers: {e}")
        return

    # --- 4) CLI starten ---
    to_network   = queue.Queue()
    from_network = queue.Queue()
    to_discovery = queue.Queue()

    print("💬 Starte CLI. Mit /help bekommst du alle Befehle.")
    try:
        cli_loop(to_network, from_network, to_discovery)
    except KeyboardInterrupt:
        print("\n👋 CLI beendet durch Benutzer.")
    except Exception as e:
        print(f"❌ Fehler in der CLI: {e}")

if __name__ == "__main__":
    main()
