import tkinter as tk
from tkinter import scrolledtext, Entry, Button, Frame, messagebox, filedialog, simpledialog
import threading
import queue
import toml
import os
import sys
from datetime import datetime

# === Konfiguration ===
def lade_konfiguration(pfad="config.toml"):
    """Lädt die Konfigurationsdatei"""
    try:
        config = toml.load(pfad)
        if not os.path.exists(config.get("imagepath", "./bilder")):
            os.makedirs(config.get("imagepath", "./bilder"))
        return config
    except Exception as e:
        messagebox.showerror("Fehler", f"Konfiguration laden fehlgeschlagen: {e}")
        sys.exit(1)

def speichere_konfiguration(config, pfad="config.toml"):
    """Speichert die Konfiguration"""
    try:
        with open(pfad, 'w') as f:
            toml.dump(config, f)
        return True
    except:
        return False

def benutzername_abfragen(config):
    """Fragt den Benutzernamen ab und speichert ihn in der Konfiguration"""
    root = tk.Tk()
    root.withdraw()
    name = simpledialog.askstring("Name wählen", "Bitte gib deinen Chat-Namen ein:", initialvalue=config.get("handle", ""))
    if name:
        config["handle"] = name
        speichere_konfiguration(config)
    else:
        messagebox.showerror("Fehler", "Kein Name eingegeben. Das Programm wird beendet.")
        sys.exit(1)
    root.destroy()

# === Chat-Anwendung ===
class ChatApp:
    def __init__(self, master, to_network=None, from_network=None, to_discovery=None):
        """Initialisiert die Chat-GUI"""
        self.master = master
        self.to_network = to_network or queue.Queue()
        self.from_network = from_network or queue.Queue()
        self.to_discovery = to_discovery or queue.Queue()
        self.config = lade_konfiguration()
        benutzername_abfragen(self.config)  # Name abfragen und speichern
        self.is_joined = False
        self.participants = set()
        
        self.setup_gui()
        threading.Thread(target=self.empfange_nachrichten, daemon=True).start()

    def setup_gui(self):
        """Erstellt die Benutzeroberfläche"""
        # Hauptfenster
        self.master.title("SLCP Chat - Gruppe A9")
        self.master.geometry("700x500")
        self.master.configure(bg='#e0e0e0')  # Heller grauer Hintergrund

        # Header
        header = Frame(self.master, bg='#cccccc', height=40)
        header.pack(fill=tk.X, padx=10, pady=(10,5))
        header.pack_propagate(False)

        self.status_label = tk.Label(header, text="● Nicht verbunden", 
                                   bg='#cccccc', fg='red', font=('Arial', 10))
        self.status_label.pack(side=tk.LEFT, pady=10)

        tk.Label(header, text=f"Benutzer: {self.config.get('handle', 'Unbekannt')}", 
                bg='#cccccc', fg='gray', font=('Arial', 9)).pack(side=tk.RIGHT, pady=10)

        # Chat-Bereich
        chat_frame = Frame(self.master, bg='#e0e0e0')
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.chat_history = scrolledtext.ScrolledText(
            chat_frame, height=20, bg='white', fg='black', font=('Arial', 10)
        )
        self.chat_history.pack(fill=tk.BOTH, expand=True)

        # Eingabebereich
        input_frame = Frame(self.master, bg='#e0e0e0')
        input_frame.pack(fill=tk.X, padx=10, pady=(5,10))

        self.message_entry = Entry(input_frame, font=('Arial', 11))
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
        self.message_entry.bind('<Return>', lambda e: self.send_message())

        # Buttons mit sichtbarem Text und Kontrast
        send_btn = Button(input_frame, text="Senden", command=self.send_message, 
               bg='#bdbdbd', fg='black', padx=15)
        send_btn.pack(side=tk.RIGHT, padx=(0,5))

        img_btn = Button(input_frame, text="Bild", command=self.send_image, 
               bg='#bdbdbd', fg='black', padx=10)
        img_btn.pack(side=tk.RIGHT, padx=(0,5))

        menu_btn = Button(input_frame, text="Menü", command=self.show_menu, 
               bg='#bdbdbd', fg='black', padx=10)
        menu_btn.pack(side=tk.RIGHT)

    def send_message(self):
        """Sendet eine Nachricht oder führt einen Befehl aus"""
        text = self.message_entry.get().strip()
        if not text:
            return
            
        # Debug-Ausgabe
        print(f"Debug: Sende Nachricht: {text}")
            
        if text.startswith('/'):
            self.handle_command(text)
        else:
            if not self.is_joined:
                self.zeige_nachricht("❌ Erst mit /join beitreten!")
                return
            # Simuliere Netzwerk-Nachricht für Testing
            try:
                self.to_network.put(f"MSG Broadcast {text}")
                self.zeige_nachricht(f"Du: {text}")
            except Exception as e:
                print(f"Debug: Fehler beim Senden: {e}")
                self.zeige_nachricht(f"Du: {text}")
                
        self.message_entry.delete(0, tk.END)

    def handle_command(self, command):
        """Verarbeitet Chat-Befehle"""
        parts = command.split(' ', 2)
        cmd = parts[0].lower()
        
        print(f"Debug: Verarbeite Befehl: {cmd}")
        
        if cmd == '/join':
            self.join_chat()
        elif cmd == '/leave':
            self.leave_chat()
        elif cmd == '/who':
            try:
                self.to_discovery.put("WHO")
                self.zeige_nachricht("🔍 Suche Teilnehmer...")
            except Exception as e:
                print(f"Debug: Fehler bei WHO: {e}")
                self.zeige_nachricht("🔍 Suche Teilnehmer... (Offline-Modus)")
        elif cmd == '/msg' and len(parts) >= 3:
            try:
                self.to_network.put(f"MSG {parts[1]} {parts[2]}")
                self.zeige_nachricht(f"An {parts[1]}: {parts[2]}")
            except Exception as e:
                print(f"Debug: Fehler bei MSG: {e}")
                self.zeige_nachricht(f"An {parts[1]}: {parts[2]}")
        elif cmd == '/help':
            self.show_help()
        elif cmd == '/exit':
            self.master.quit()
        else:
            self.zeige_nachricht("❌ Unbekannter Befehl. /help für Hilfe")

    def join_chat(self):
        """Tritt dem Chat bei"""
        if self.is_joined:
            self.zeige_nachricht("⚠️ Bereits beigetreten!")
            return
        try:
            self.to_discovery.put(f"JOIN {self.config['handle']} {self.config['port']}")
        except Exception as e:
            print(f"Debug: Discovery nicht verfügbar: {e}")
        
        self.is_joined = True
        self.status_label.config(text="● Verbunden", fg='green')
        self.zeige_nachricht(f"✅ Chat beigetreten als '{self.config['handle']}'")

    def leave_chat(self):
        """Verlässt den Chat"""
        if not self.is_joined:
            self.zeige_nachricht("⚠️ Nicht im Chat!")
            return
        try:
            self.to_discovery.put(f"LEAVE {self.config['handle']}")
        except Exception as e:
            print(f"Debug: Discovery nicht verfügbar: {e}")
        
        self.is_joined = False
        self.status_label.config(text="● Getrennt", fg='red')
        self.zeige_nachricht("👋 Chat verlassen")

    def send_image(self):
        """Sendet ein Bild"""
        if not self.is_joined:
            self.zeige_nachricht("❌ Erst dem Chat beitreten!")
            return
        file_path = filedialog.askopenfilename(
            title="Bild auswählen",
            filetypes=[("Bilder", "*.png *.jpg *.jpeg *.gif *.bmp")]
        )
        if file_path:
            try:
                self.to_network.put(f"IMG Broadcast {file_path}")
                self.zeige_nachricht(f"🖼️ Bild gesendet: {os.path.basename(file_path)}")
            except Exception as e:
                print(f"Debug: Fehler beim Bildversand: {e}")
                self.zeige_nachricht(f"🖼️ Bild ausgewählt: {os.path.basename(file_path)}")

    def show_menu(self):
        """Zeigt das Hauptmenü"""
        print("Debug: Zeige Menü")
        menu = tk.Menu(self.master, tearoff=0)
        menu.add_command(label="📥 Beitreten", command=self.join_chat)
        menu.add_command(label="📤 Verlassen", command=self.leave_chat)
        menu.add_command(label="👥 Teilnehmer", command=lambda: self.handle_command('/who'))
        menu.add_command(label="❓ Hilfe", command=self.show_help)
        menu.add_command(label="🚪 Beenden", command=self.master.quit)
        
        try:
            menu.tk_popup(self.master.winfo_pointerx(), self.master.winfo_pointery())
        finally:
            menu.grab_release()

    def show_help(self):
        """Zeigt die Hilfe"""
        help_text = """
SLCP Chat - Befehle:
/join - Chat beitreten
/leave - Chat verlassen  
/who - Teilnehmer suchen
/msg <user> <text> - Private Nachricht
/exit - Beenden
/help - Diese Hilfe
        """
        self.zeige_nachricht(help_text)

    def empfange_nachrichten(self):
        """Thread für eingehende Nachrichten"""
        while True:
            try:
                msg = self.from_network.get(timeout=1)
                self.zeige_nachricht(f"📥 {msg}")
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Debug: Fehler beim Empfangen: {e}")
                continue

    def zeige_nachricht(self, text):
        """Zeigt eine Nachricht im Chat an"""
        timestamp = datetime.now().strftime("%H:%M")
        try:
            self.chat_history.insert(tk.END, f"[{timestamp}] {text}\n")
            self.chat_history.see(tk.END)
        except Exception as e:
            print(f"Debug: Fehler beim Anzeigen der Nachricht: {e}")

def main():
    """Startet die Anwendung"""
    to_network = queue.Queue()
    from_network = queue.Queue()
    to_discovery = queue.Queue()

    root = tk.Tk()
    app = ChatApp(root, to_network, from_network, to_discovery)
    root.protocol("WM_DELETE_WINDOW", lambda: root.quit())
    
    # Debug-Ausgabe
    print("Debug: GUI gestartet")
    
    root.mainloop()

if __name__ == "__main__":
    main()
