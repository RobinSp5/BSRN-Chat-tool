import sys
import threading
import queue
import toml
import os

# === Funktion: Hilfetext anzeigen ===
def print_help():
    print("""
Verfügbare Befehle:
  /join                - Dem Chat beitreten
  /leave               - Chat verlassen
  /who                 - Teilnehmer im Netzwerk suchen
  /msg <User> <Text>   - Nachricht an Nutzer senden
  /img <User> <Pfad>   - Bild an Nutzer senden
  /exit                - Programm beenden
  /help                - Hilfe anzeigen
""")

# === Funktion: Konfiguration aus config.toml laden ===
def lade_konfiguration(pfad="config.toml"):
    try:
        config = toml.load(pfad)
   
        # Prüfen, ob Bildordner existiert – wenn nicht: erstellen
        image_dir = config.get("imagepath", "./bilder")
        if not os.path.exists(image_dir):
            os.makedirs(image_dir)

        return config
    except Exception as e:
        print(f"Fehler beim Laden der Konfiguration: {e}")
        sys.exit(1)

# === Hauptfunktion für das CLI ===
def cli_loop(to_network, from_network, to_discovery):
    # Konfiguration laden
    config = lade_konfiguration()

    print("Willkommen im SLCP-Chat (CLI-Version)")
    print(f"Angemeldet als: {config['handle']}")
    print_help()

    # === Thread: empfängt Nachrichten aus dem Netzwerk und zeigt sie an ===
    def incoming_messages_listener():
        while True:
            try:
                msg = from_network.get(timeout=1)
                print(f"\n[Empfangen] {msg}")
            except queue.Empty:
                continue

    threading.Thread(target=incoming_messages_listener, daemon=True).start()

    # === Haupt-CLI-Eingabeschleife ===
    while True:
        try:
            user_input = input(">>> ").strip()

            if not user_input:
                continue

            parts = user_input.split(" ", 2)

            # === Chat verlassen ===
            if parts[0] == "/exit":
                print("Programm wird beendet...")
                break

            # === JOIN senden ===
            elif parts[0] == "/join":
                to_discovery.put(f"JOIN {config['handle']} {config['port']}")
                print(f"Beitritt gesendet: {config['handle']}")

            # === LEAVE senden ===
            elif parts[0] == "/leave":
                to_discovery.put(f"LEAVE {config['handle']}")
                print("Verlasse den Chat...")

            # === WHO senden ===
            elif parts[0] == "/who":
                to_discovery.put("WHO")
                print("Frage nach aktiven Nutzern gesendet...")

            # === MSG senden ===
            elif parts[0] == "/msg" and len(parts) >= 3:
                handle, text = parts[1], parts[2]
                if config.get("away", False):
                    to_network.put(f"MSG {handle} {config.get('autoreply', 'Ich bin nicht verfügbar.')}")
                    print(f"[Abwesenheitsantwort an {handle}]")
                else:
                    to_network.put(f"MSG {handle} {text}")
                    print(f"[Gesendet an {handle}]: {text}")

            # === IMG senden ===
            elif parts[0] == "/img" and len(parts) >= 3:
                handle, path = parts[1], parts[2]
                try:
                    with open(path, "rb") as f:
                        image_data = f.read()
                    to_network.put((f"IMG {handle} {len(image_data)}", image_data))
                    print(f"[Bild gesendet an {handle}] Größe: {len(image_data)} Bytes")
                except FileNotFoundError:
                    print(f"Datei nicht gefunden: {path}")

            # === Hilfe anzeigen ===
            elif parts[0] == "/help":
                print_help()
            else:
                print("Unbekannter Befehl. /help zeigt alle Optionen.")

        except (KeyboardInterrupt, EOFError):
            print("\nBeende CLI...")
            break
