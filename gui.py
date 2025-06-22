import tkinter as tk
from tkinter import ttk
from tkinter import simpledialog
import time
import os
import toml
import socket

# Importiere die benötigten Module
from ipc_handler import IPCHandler
from discovery import DiscoveryService
from chat_client import ChatClient
from chat_server import ChatServer


class ChatGUI:
    def __init__(self, root):

        # Hier wird das Fenster zusammen gebaut via Tkinter
        # Alle Buttons werden definiert
        # Fenster-Einstellungen und auch die Box in welcher die aktiven Nutzer angezeigt werden
        self.root = root
        self.root.title("BSRN Chat Tool")
        self.root.geometry("800x600")

        # Main frame
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Chat display area (placeholder)
        self.chat_display = tk.Text(main_frame, height=20, width=70, state='disabled')
        self.chat_display.grid(row=0, column=1, columnspan=3, pady=(0, 10), sticky=(tk.W, tk.E, tk.N, tk.S))

        # Active users area
        users_label = ttk.Label(main_frame, text="Aktive Nutzer:")
        users_label.grid(row=0, column=0, sticky=(tk.W, tk.N), padx=(0, 10))

        self.users_listbox = tk.Listbox(main_frame, width=20, height=20)
        self.users_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        self.users_listbox.bind("<Double-Button-1>", self.on_user_double_click)


        # Message input
        self.message_entry = tk.Entry(main_frame, width=50)
        self.message_entry.grid(row=1, column=1, columnspan=2, pady=(0, 10), sticky=(tk.W, tk.E))

        # Send button
        self.send_button = ttk.Button(main_frame, text="Senden", command=self.send_message)
        self.send_button.grid(row=1, column=3, padx=(5, 0), pady=(0, 10))

        # Control buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=1, columnspan=3, pady=(0, 5), sticky=(tk.W, tk.E))

        self.clear_button = ttk.Button(button_frame, text="Chat löschen", command=self.clear_chat)
        self.clear_button.pack(side=tk.LEFT, padx=(0, 5))

        self.disconnect_button = ttk.Button(button_frame, text="Quit", command=self.disconnect_from_server)
        self.disconnect_button.pack(side=tk.RIGHT)

        self.refresh_button = ttk.Button(button_frame, text="Aktualisieren", command=self.update_active_users)
        self.refresh_button.pack(side=tk.RIGHT, padx=(5, 0))

        # Configure grid weights
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)
        





        # Ab hier beginnt die initialisierung der Chat Logik
        # DiscoveryService und IPCHandler werden initialisiert usw...

        # Config laden (relativer Pfad zur gui.py)
        cfg_path = os.path.join(os.path.dirname(__file__), "config.toml")
        config   = toml.load(cfg_path)

        #
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
        finally:
            s.close()
        config['network']['local_ip'] = local_ip

        # Unsename bzw. Handle aus der config.toml Datei auslesen
        try:
            self.username = config['handle']  # Direkter Zugriff auf handle
        #Falls handle nicht gefunden, dann unter [user] section nachsehen
        except KeyError:
            try:
                self.username = config['user']['handle']  # Falls unter [user] section
            except KeyError:
                self.username = 'DefaultUser'  # Fallback
                print(f"handle nicht in config.toml gefunden. Verwende: {self.username}")
        
        #print(f"Verwende Username: {self.username}") # Terminal output für Debugging

        self.username = None  # Initialisiere den Username
        self.username_abfragen()  # Frage den Username ab

        # IPC-Handler und Discovery-Service initialisieren
        chat_tcp_port     = config["network"].get("chat_port", 5001)
        self.ipc_handler  = IPCHandler()
        self.discovery    = DiscoveryService(config, self.ipc_handler, self.username, chat_tcp_port)

        # Autoreply standard deaktiviert
        self.autoreply_active = False
        
        # Chat-Client initialisieren
        self.chat_client = ChatClient(config, self.username)

        # Chat-Server initialisieren
        self.chat_server = ChatServer(config, self.ipc_handler)
        self.chat_server.start()

        self.discovery.start()  # Discovery-Service starten
        self.is_connected = True  # Status der Verbindung
        self.discovery.send_join()
        self.display_system_message(f"JOIN als '{self.username}' versendet")

        time.sleep(0.5)  # Kurze Pause, um sicherzustellen, dass Discovery gestartet ist
        self.discovery.request_discovery()  # Discovery anfordern


        
        # Starte die Nutzer-Aktualisierung
        self.start_user_update_loop()

        # Starte die Nachrichten-Abfrage
        self.start_message_polling()


#-------------------------------------------------------------------------------------------------------------

    # Ab hier werden die Funktionen definiert, die die GUI steuern
    # Diese Funktionen werden von den Buttons aufgerufen
    # und steuern die Logik des Chat-Programms


    # Aktualisiert die Liste der aktiven Nutzer
    def update_active_users(self):
        """Aktualisiert die Liste der aktiven Nutzer"""
        # Liste leeren
        self.users_listbox.delete(0, tk.END)

        # ← FIX: Prüfen ob is_connected existiert
        is_connected = getattr(self, 'is_connected', False)

        # Eigenen Username anzeigen (wenn verbunden)
        if is_connected:
            local_ip = self.chat_client.config['network'].get('local_ip', 'localhost')
            chat_port = self.chat_client.config['network'].get('chat_port', 5001)
            self.users_listbox.insert(tk.END, f"{self.username} (Du) @ {local_ip}:{chat_port}")

        # ← FIX: Nur aktive und erreichbare Nutzer anzeigen
        users = self.ipc_handler.get_active_users()
        active_users = []
        
        for name, info in users.items():
            if name != self.username:
                status = info.get('status', 'online')
                last_seen = info.get('last_seen', 0)
                current_time = time.time()
                
                # Nur Nutzer anzeigen die in den letzten 90 Sekunden aktiv waren
                if current_time - last_seen < 90 and status == 'online':
                    active_users.append((name, info))
        
        if not active_users:
            self.users_listbox.insert(tk.END, "Keine anderen Nutzer online")
        else:
            for name, info in active_users:
                user_display = f"{name} @ {info['ip']}:{info['tcp_port']}"
                self.users_listbox.insert(tk.END, user_display)

    # Startet eine Schleife, die alle 500 ms die aktiven Nutzer aktualisiert
    def start_user_update_loop(self):
        # alle 500ms neu laden
        self.update_active_users()
        self.root.after(500, self.start_user_update_loop)

    # Startet die Nachrichten-Abfrage
    def start_message_polling(self):
        self.poll_messages()
    
    # Startet eine Schleife, die alle 100 ms auf neue Nachrichten prüft
    def poll_messages(self):
        msg = self.ipc_handler.get_message(timeout=0.1)
        if msg:
            self.display_message(msg)
        # Wiederhole alle 100ms
        self.root.after(100, self.poll_messages)

    # Zeigt eine Nachricht im Chat-Fenster an
    def display_message(self, message):
        msg_type  = message.get('type')
        sender_ip = message.get('sender_ip', 'Unbekannt')
        timestamp = message.get('timestamp', time.time())
        ts        = time.strftime('%H:%M:%S', time.localtime(timestamp))

        # ← FIX: Bessere Namensauflösung
        sender_name = None
        local_ip = self.chat_client.config['network'].get('local_ip', '')
        
        # Erst nach IP in der Nutzerliste suchen
        users = self.ipc_handler.get_active_users(only_visible=False)
        for name, info in users.items():
            if info.get('ip') == sender_ip:
                sender_name = name
                break
        
        # Falls es die eigene IP ist, aber kein Name gefunden wurde
        if sender_ip == local_ip and not sender_name:
            sender_name = self.username  # ← Verwendet jetzt self.username statt chat_client.username

        # Format: Name (IP) für bessere Klarheit
        if sender_name:
            display_name = f"{sender_name} ({sender_ip})"
        else:
            display_name = sender_ip

        # Nachrichtentypen unterscheiden
        if msg_type == 'text':
            content = message.get('content', '')
            recipient = message.get('recipient', '')
            if recipient == self.username:
                line = f"[{ts}] [PM] {display_name}: {content}\n"
            else:
                line = f"[{ts}] {display_name}: {content}\n"
            
        elif msg_type == 'image':
            fname = message.get('filename', '')
            line = f"[{ts}] {display_name} schickte ein Bild: {fname}\n"
        elif msg_type == 'system':
            content = message.get('content', '')
            line = f"[{ts}] SYSTEM: {content}\n"
        else:
            line = f"[{ts}] Unbekannte Nachricht: {message}\n"

        # Im Text-Widget einfügen
        self.chat_display.configure(state='normal')
        self.chat_display.insert(tk.END, line)
        self.chat_display.see(tk.END)
        self.chat_display.configure(state='disabled')

    # Zeigt eine Systemnachricht im Chat-Fenster an
    def display_system_message(self, text):
        self.chat_display.configure(state='normal')
        ts = time.strftime('%H:%M:%S', time.localtime())
        line = f"[{ts}] {text}\n"
        self.chat_display.insert(tk.END, line)
        self.chat_display.see(tk.END)
        self.chat_display.configure(state='disabled')

    def username_abfragen(self):
        new_username = simpledialog.askstring(
            "Username eingeben",
            "Bitte gib deinen Chat-Benutzernamen ein:",
            parent=self.root,
            initialvalue=getattr(self, "username", "")
        )
        if not new_username or not new_username.strip():
            # kein Username → Abbruch
            self.username = None
            return
        self.username = new_username.strip()
        # DiscoveryService und ChatClient updaten, falls sie schon existieren
        if hasattr(self, "chat_client"):
            self.chat_client.username = self.username
        if hasattr(self, "discovery"):
            self.discovery.username = self.username
            # handle in config.toml überschreiben
            cfg_path = os.path.join(os.path.dirname(__file__), "config.toml")
            # Je nach Schema: top-level handle oder unter [user]
            try:
                # wenn top-level
                self.config['handle'] = self.username
            except KeyError:
                # fallback in [user]
                self.config.setdefault('user', {})['handle'] = self.username
            # config wieder speichern
            with open(cfg_path, "w") as f:
                toml.dump(self.config, f)

            self.display_system_message(f"Username gesetzt: {self.username}")


#-------------------------------------------------------------------------------------------------------------

    # Ab hier wird definiert was passiert,
    # wenn die Buttons in der GUI gedrückt werden


    # Senden-Button ()
    def send_message(self):
        self.discovery.request_discovery() # Discovery erneut anfordern
        text = self.message_entry.get().strip()
        if not text:
            return
        
        users = self.ipc_handler.get_active_users()
        sent_count = 0
        for name, info in users.items():
            # ← FIX: Vergleiche mit self.username statt chat_client.username
            if name != self.username:
                try:
                    success = self.chat_client.send_text_message(
                        info['ip'], info['tcp_port'], name, text
                    )
                    if success:
                        sent_count += 1
                except Exception as e:
                    print(f"Fehler beim Senden an {name}: {e}")
        
        # Eigene Nachricht anzeigen
        self.display_system_message(f"Du ({self.username}): {text} (an {sent_count} Nutzer gesendet)")
        
        # Eingabe leeren
        self.message_entry.delete(0, tk.END)

    # Doppelklick auf einen Nutzer in der Liste und pm
    def on_user_double_click(self, event):
        try:
            index = self.users_listbox.curselection()[0]
            selected = self.users_listbox.get(index)
        except IndexError:
            self.display_system_message("Kein Nutzer ausgewählt.")
            return

        if "@" not in selected:
            self.display_system_message("Kein gültiger Nutzer.")
            return

        recipient = selected.split(" @ ")[0]

        message = simpledialog.askstring(
            f"Privatnachricht an {recipient}",
            "Nachricht eingeben:"
        )

        if not message:
            return

        users = self.ipc_handler.get_active_users()
        info = users.get(recipient)
        if not info:
            self.display_system_message(f"{recipient} nicht erreichbar.")
            return

        if self.chat_client.send_text_message(info["ip"], info["tcp_port"], recipient, message):
            self.display_system_message(f"[PM] Du → {recipient}: {message}")



    #Aktualisiern-Button
    def refresh_users(self):
        self.discovery.request_discovery()  # Discovery erneut anfordern
        self.update_active_users()  # Nutzerliste aktualisieren

    # Quit-Button um das Programm zu beenden
    def disconnect_from_server(self):
        self.discovery.send_leave()
        self.root.quit()
        self.root.destroy()

    def clear_chat(self):
        self.chat_display.configure(state='normal')
        self.chat_display.delete(1.0, tk.END)
        self.chat_display.configure(state='disabled')

if __name__ == "__main__":
    root = tk.Tk()
    app = ChatGUI(root)
    root.mainloop()