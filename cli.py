import sys
import threading
import queue

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

def cli_loop(to_network, from_network, to_discovery, config):
    print("Willkommen im SLCP-Chat (CLI-Version)")
    print_help()

    def incoming_messages_listener():
        while True:
            try:
                msg = from_network.get(timeout=1)
                print(f"\n[Empfangen] {msg}")
            except queue.Empty:
                continue

    threading.Thread(target=incoming_messages_listener, daemon=True).start()

    while True:
        try:
            user_input = input(">>> ").strip()

            if not user_input:
                continue

            parts = user_input.split(" ", 2)

            if parts[0] == "/exit":
                print("Programm wird beendet...")
                break

            elif parts[0] == "/join":
                to_discovery.put(f"JOIN {config['handle']} {config['port']}")
                print(f"Beitritt gesendet: {config['handle']}")

            elif parts[0] == "/leave":
                to_discovery.put(f"LEAVE {config['handle']}")
                print("Verlasse den Chat...")

            elif parts[0] == "/who":
                to_discovery.put("WHO")
                print("Frage nach aktiven Nutzern gesendet...")

            elif parts[0] == "/msg" and len(parts) >= 3:
                handle, text = parts[1], parts[2]
                to_network.put(f"MSG {handle} {text}")
                print(f"[Gesendet an {handle}]: {text}")

            elif parts[0] == "/img" and len(parts) >= 3:
                handle, path = parts[1], parts[2]
                try:
                    with open(path, "rb") as f:
                        image_data = f.read()
                    to_network.put((f"IMG {handle} {len(image_data)}", image_data))
                    print(f"[Bild gesendet an {handle}] Größe: {len(image_data)} Bytes")
                except FileNotFoundError:
                    print(f"Datei nicht gefunden: {path}")

            elif parts[0] == "/help":
                print_help()
            else:
                print("Unbekannter Befehl. /help zeigt alle Optionen.")

        except (KeyboardInterrupt, EOFError):
            print("\nBeende CLI...")
            break
