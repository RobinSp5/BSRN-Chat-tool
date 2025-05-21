import sys
import threading
import queue
import toml
import os
  
# === Zeigt alle verfügbaren Befehle an ===
def print_help():
    print("Verfügbare Befehle:")
    print("  /join                - Dem Chat beitreten")
    print("  /leave               - Chat verlassen")
    print("  /who                 - Teilnehmer im Netzwerk suchen")
    print("  /msg <User> <Text>   - Nachricht an Nutzer senden")
    print("  /img <User> <Pfad>   - Bild an Nutzer senden")
    print("  /set <Schlüssel> <Wert> - Konfiguration ändern und speichern")
    print("  /exit                - Programm beenden")
    print("  /help                - Hilfe anzeigen")

# === Lädt die Konfiguration aus der config.toml Datei ===
def lade_konfiguration(pfad="config.toml"):
    try:
        config = toml.load(pfad)
   
        # Prüfen, ob Bildordner existiert – wenn nicht: erstellen
        image_dir = config.get("imagepath", "./bilder")
        if not os.path.exists(image_dir):
            os.makedirs(image_dir)

        return config
    except FileNotFoundError:
        print("Die Datei config.toml wurde nicht gefunden. Bitte anlegen oder Pfad prüfen.")
        sys.exit(1)
    except Exception as e:
        print(f"Fehler beim Laden der Konfiguration: {e}")
        sys.exit(1)

# === Startet das CLI (Command Line Interface) ===
def cli_loop(to_network, from_network, to_discovery):
    # Konfiguration laden
    config = lade_konfiguration()

    print("Willkommen im SLCP-Chat (CLI-Version)")
    print("Angemeldet als:", config.get("handle", "Unbekannt"))
    print_help()

    # === Thread: empfängt Nachrichten aus dem Netzwerk und zeigt sie an ===
    def nachrichten_empfangen():
        while True:
            try:
                 # Neue Nachricht aus der Empfangs-Queue holen
                msg = from_network.get(timeout=1)
                print(f"\n[Empfangen] {msg}")
            except queue.Empty:
                  # Keine Nachricht vorhanden → erneut warten
                continue

   # Startet den Empfangs-Thread im Hintergrund
    threading.Thread(target=nachrichten_empfangen, daemon=True).start()


    # === Haupt-CLI-Eingabeschleife ===
    while True:
        try:
            eingabe = input(">>> ").strip()

            if not eingabe:
                continue # Leere Eingabe ignorieren

            teile = eingabe.split(" ", 2) # Befehl aufteilen (max. 3 Teile)
            befehl = teile[0]

            # === Programm beenden bzw. Chat verlassen  ===
            if befehl == "/exit":
                print("Programm wird beendet...")
                break

             # === Dem Chat beitreten (JOIN) ===
            elif befehl == "/join":
                to_discovery.put(f"JOIN {config['handle']} {config['port']}")
                print("JOIN gesendet")
                
            # === Chat verlassen (LEAVE) ===
            elif befehl == "/leave":
                to_discovery.put(f"LEAVE {config['handle']}")
                print("LEAVE gesendet")
                
            # === Teilnehmer im Netzwerk erfragen (WHO) ===
            elif befehl == "/who":
                to_discovery.put("WHO")
                print("WHO gesendet")

            # === Nachricht an anderen Nutzer senden (MSG) ===
            elif befehl == "/msg":
                if len(teile) < 3:
                    print("Fehlendes Argument: /msg <User> <Text>")
                else:
                    empfaenger, text = teile[1], teile[2]
                     # Prüfen, ob Abwesenheitsmodus aktiv ist
                    if config.get("away", False):
                        antwort = config.get("autoreply", "Ich bin gerade nicht da.")
                        to_network.put(f"MSG {empfaenger} {antwort}")
                        print(f"[Abwesenheitsantwort an {empfaenger}]")
                    else:
                        to_network.put(f"MSG {empfaenger} {text}")
                        print(f"[Gesendet an {empfaenger}]: {text}")
                        
            
            # === Bild an anderen Nutzer senden (IMG) ===
            elif befehl == "/img":
                if len(teile) < 3: # === LEN gibt dir die Länge eines Objekts zurück, also es zählt die WÖRTEr nicht BUCHSTABEN ===
                    print("Fehlendes Argument: /img <User> <Pfad>")
                else:
                    empfaenger, pfad = teile[1], teile[2]
                    try:
                        # Bild öffnen und als Bytes lesen
                        with open(pfad, "rb") as f:
                            bilddaten = f.read()
                             # Bild inklusive Header in Netzwerk-Queue senden
                        to_network.put((f"IMG {empfaenger} {len(bilddaten)}", bilddaten))
                        print("Bild an", empfaenger, "gesendet – Größe:", len(bilddaten), "Bytes")
                    except FileNotFoundError:
                        print("Bilddatei nicht gefunden:", pfad)
  # === Konfiguration ändern und speichern (/set) ===
            elif befehl == "/set":
                if len(teile) < 3:
                    print("Syntax: /set <Schlüssel> <Wert>")
                else:
                    schluessel, wert = teile[1], teile[2]
                    config[schluessel] = wert
                    try:
                        # Änderungen in config.toml speichern
                        with open("config.toml", "w") as f:
                            toml.dump(config, f)
                        print(f"Konfig geändert: {schluessel} = {wert}")
                    except Exception as e:
                        print("Fehler beim Schreiben der Konfig:", e)
# === Hilfe anzeigen ===
            elif befehl == "/help":
                print_help()
# === Ungültiger Befehl eingegeben ===
            else:
                print("Unbekannter Befehl. Mit /help bekommst du eine Übersicht.")

        except (KeyboardInterrupt, EOFError):
            print("\nBeende CLI...")
            break
