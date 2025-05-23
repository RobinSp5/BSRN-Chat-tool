import tkinter as tk
from tkinter import scrolledtext, Entry, Button, Frame, messagebox, filedialog, ttk
import threading
import queue
import toml
import os
import sys
from datetime import datetime

# === Konfigurationsfunktion ===
def lade_konfiguration(pfad="config.toml"):
    try:
        config = toml.load(pfad)
        image_dir = config.get("imagepath", "./bilder")
        if not os.path.exists(image_dir):
            os.makedirs(image_dir)
        return config
    except Exception as e:
        messagebox.showerror("Konfigurationsfehler", f"Fehler beim Laden von config.toml: {e}")
        sys.exit(1)

def speichere_konfiguration(config, pfad="config.toml"):
    try:
        with open(pfad, 'w') as f:
            toml.dump(config, f)
        return True
    except Exception as e:
        messagebox.showerror("Fehler", f"Konfiguration konnte nicht gespeichert werden: {e}")
        return False

# === GUI-Anwendung ===
class ChatApp:
    def __init__(self, master, to_network, from_network, to_discovery):
        self.master = master
        self.to_network = to_network
        self.from_network = from_network
        self.to_discovery = to_discovery
        self.config = lade_konfiguration()
        self.is_joined = False
        self.participants = set()

        # WICHTIG: setup_styles() MUSS vor setup_gui() aufgerufen werden
        self.setup_styles()
        self.setup_gui()
        
        # Nachrichten-Thread starten
        threading.Thread(target=self.empfange_nachrichten, daemon=True).start()

    def setup_styles(self):
        # Moderne Farben
        self.colors = {
            'bg_primary': '#2c3e50',
            'bg_secondary': '#34495e',
            'bg_chat': '#ecf0f1',
            'text_primary': '#2c3e50',
            'text_secondary': '#7f8c8d',
            'accent': '#3498db',
            'success': '#27ae60',
            'warning': '#f39c12',
            'danger': '#e74c3c'
        }

    def setup_gui(self):
        self.master.title("SLCP Chat - Gruppe A9")
        self.master.geometry("800x600")
        self.master.configure(bg='#2c3e50')
        
        # Hauptcontainer
        main_frame = Frame(self.master, bg='#2c3e50')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Header mit Status
        self.setup_header(main_frame)
        
        # Chat-Bereich
        self.setup_chat_area(main_frame)
        
        # Teilnehmer-Liste (Sidebar)
        self.setup_participants_sidebar(main_frame)
        
        # Eingabebereich
        self.setup_input_area(main_frame)
        
        # Statusleiste
        self.setup_status_bar(main_frame)

    def setup_header(self, parent):
        header_frame = Frame(parent, bg=self.colors['bg_secondary'], height=50)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        header_frame.pack_propagate(False)
        
        # Status-Label
        self.status_label = tk.Label(
            header_frame, 
            text="● Nicht verbunden", 
            bg=self.colors['bg_secondary'], 
            fg=self.colors['danger'],
            font=('Arial', 12, 'bold')
        )
        self.status_label.pack(side=tk.LEFT, padx=10, pady=10)
        
        # Benutzer-Info
        user_info = f"Benutzer: {self.config.get('handle', 'Unbekannt')}"
        self.user_label = tk.Label(
            header_frame, 
            text=user_info, 
            bg=self.colors['bg_secondary'], 
            fg='white',
            font=('Arial', 10)
        )
        self.user_label.pack(side=tk.RIGHT, padx=10, pady=10)

    def setup_chat_area(self, parent):
        # Container für Chat und Teilnehmer
        content_frame = Frame(parent, bg=self.colors['bg_primary'])
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Chat-Bereich
        chat_frame = Frame(content_frame, bg=self.colors['bg_primary'])
        chat_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        tk.Label(
            chat_frame, 
            text="Chat-Verlauf", 
            bg=self.colors['bg_primary'], 
            fg='white',
            font=('Arial', 12, 'bold')
        ).pack(anchor='w', pady=(0, 5))
        
        self.chat_history = scrolledtext.ScrolledText(
            chat_frame, 
            wrap=tk.WORD, 
            width=60, 
            height=20, 
            state='disabled',
            bg=self.colors['bg_chat'],
            fg=self.colors['text_primary'],
            font=('Consolas', 10)
        )
        self.chat_history.pack(fill=tk.BOTH, expand=True)

    def setup_participants_sidebar(self, parent):
        # Teilnehmer-Sidebar
        sidebar_frame = Frame(parent.winfo_children()[-1], bg=self.colors['bg_secondary'], width=200)
        sidebar_frame.pack(side=tk.RIGHT, fill=tk.Y)
        sidebar_frame.pack_propagate(False)
        
        tk.Label(
            sidebar_frame, 
            text="Teilnehmer", 
            bg=self.colors['bg_secondary'], 
            fg='white',
            font=('Arial', 12, 'bold')
        ).pack(pady=10)
        
        self.participants_listbox = tk.Listbox(
            sidebar_frame,
            bg='white',
            fg=self.colors['text_primary'],
            font=('Arial', 10),
            selectbackground=self.colors['accent']
        )
        self.participants_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

    def setup_input_area(self, parent):
        input_frame = Frame(parent, bg=self.colors['bg_primary'])
        input_frame.pack(fill=tk.X, pady=10)
        
        # Eingabefeld
        self.message_entry = Entry(
            input_frame, 
            font=('Arial', 11),
            bg='white',
            fg=self.colors['text_primary']
        )
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.message_entry.bind('<Return>', lambda e: self.send_message())
        
        # Button-Container
        button_frame = Frame(input_frame, bg=self.colors['bg_primary'])
        button_frame.pack(side=tk.RIGHT)
        
        # Senden-Button
        send_btn = Button(
            button_frame, 
            text="Senden", 
            command=self.send_message,
            bg=self.colors['accent'],
            fg='white',
            font=('Arial', 10, 'bold'),
            padx=20
        )
        send_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Bild-Button
        img_btn = Button(
            button_frame, 
            text="📷", 
            command=self.send_image,
            bg=self.colors['success'],
            fg='white',
            font=('Arial', 12),
            width=3
        )
        img_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Menu-Button
        menu_btn = Button(
            button_frame, 
            text="⚙️", 
            command=self.show_menu,
            bg=self.colors['warning'],
            fg='white',
            font=('Arial', 12),
            width=3
        )
        menu_btn.pack(side=tk.LEFT)

    def setup_status_bar(self, parent):
        self.status_bar = tk.Label(
            parent, 
            text="Bereit | Verwende /help für Befehle", 
            bg=self.colors['bg_secondary'], 
            fg='white',
            font=('Arial', 9),
            anchor='w'
        )
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def send_message(self):
        text = self.message_entry.get().strip()
        if not text:
            return
            
        # Command-Verarbeitung
        if text.startswith('/'):
            self.handle_command(text)
        else:
            if not self.is_joined:
                self.zeige_nachricht("❌ Fehler: Erst mit /join dem Chat beitreten!", 'error')
                return
                
            empfaenger = "Broadcast"
            if self.config.get("away", False):
                antwort = self.config.get("autoreply", "Ich bin gerade nicht da.")
                self.to_network.put(f"MSG {empfaenger} {antwort}")
                self.zeige_nachricht(f"🤖 [Abwesenheitsantwort an {empfaenger}] {antwort}", 'auto')
            else:
                self.to_network.put(f"MSG {empfaenger} {text}")
                self.zeige_nachricht(f"📤 [Du an {empfaenger}]: {text}", 'sent')
                
        self.message_entry.delete(0, tk.END)

    def handle_command(self, command):
        parts = command.split(' ', 2)
        cmd = parts[0].lower()
        
        if cmd == '/join':
            self.join_chat()
        elif cmd == '/leave':
            self.leave_chat()
        elif cmd == '/who':
            self.search_participants()
        elif cmd == '/msg':
            if len(parts) >= 3:
                self.send_private_message(parts[1], parts[2])
            else:
                self.zeige_nachricht("❌ Verwendung: /msg <benutzer> <nachricht>", 'error')
        elif cmd == '/img':
            if len(parts) >= 2:
                self.send_image_to_user(parts[1])
            else:
                self.zeige_nachricht("❌ Verwendung: /img <benutzer>", 'error')
        elif cmd == '/set':
            if len(parts) >= 3:
                self.set_config(parts[1], parts[2])
            else:
                self.show_config_dialog()
        elif cmd == '/exit':
            self.exit_application()
        elif cmd == '/help':
            self.show_help()
        else:
            self.zeige_nachricht(f"❌ Unbekannter Befehl: {cmd}. Verwende /help für Hilfe.", 'error')

    def join_chat(self):
        if self.is_joined:
            self.zeige_nachricht("⚠️ Du bist bereits dem Chat beigetreten!", 'warning')
            return
            
        self.to_discovery.put(f"JOIN {self.config['handle']} {self.config['port']}")
        self.is_joined = True
        self.status_label.config(text="● Verbunden", fg=self.colors['success'])
        self.zeige_nachricht(f"✅ Dem Chat als '{self.config['handle']}' beigetreten!", 'success')
        self.status_bar.config(text="Verbunden | Online")

    def leave_chat(self):
        if not self.is_joined:
            self.zeige_nachricht("⚠️ Du bist nicht im Chat!", 'warning')
            return
            
        self.to_discovery.put(f"LEAVE {self.config['handle']}")
        self.is_joined = False
        self.status_label.config(text="● Getrennt", fg=self.colors['danger'])
        self.zeige_nachricht("👋 Chat verlassen!", 'info')
        self.participants.clear()
        self.update_participants_list()
        self.status_bar.config(text="Getrennt | Offline")

    def search_participants(self):
        self.to_discovery.put("WHO")
        self.zeige_nachricht("🔍 Suche nach Teilnehmern...", 'info')

    def send_private_message(self, user, message):
        if not self.is_joined:
            self.zeige_nachricht("❌ Erst dem Chat beitreten!", 'error')
            return
            
        self.to_network.put(f"MSG {user} {message}")
        self.zeige_nachricht(f"📨 [Privat an {user}]: {message}", 'private')

    def send_image(self):
        if not self.is_joined:
            self.zeige_nachricht("❌ Erst dem Chat beitreten!", 'error')
            return
            
        file_path = filedialog.askopenfilename(
            title="Bild auswählen",
            filetypes=[("Bilder", "*.png *.jpg *.jpeg *.gif *.bmp")]
        )
        if file_path:
            empfaenger = "Broadcast"
            self.to_network.put(f"IMG {empfaenger} {file_path}")
            self.zeige_nachricht(f"🖼️ [Bild an {empfaenger}]: {os.path.basename(file_path)}", 'image')

    def send_image_to_user(self, user):
        if not self.is_joined:
            self.zeige_nachricht("❌ Erst dem Chat beitreten!", 'error')
            return
            
        file_path = filedialog.askopenfilename(
            title="Bild auswählen",
            filetypes=[("Bilder", "*.png *.jpg *.jpeg *.gif *.bmp")]
        )
        if file_path:
            self.to_network.put(f"IMG {user} {file_path}")
            self.zeige_nachricht(f"🖼️ [Bild an {user}]: {os.path.basename(file_path)}", 'image')

    def set_config(self, key, value):
        # Konfiguration setzen
        if key in ['away']:
            self.config[key] = value.lower() in ['true', '1', 'ja', 'yes']
        elif key in ['port']:
            try:
                self.config[key] = int(value)
            except ValueError:
                self.zeige_nachricht(f"❌ Ungültiger Wert für {key}: {value}", 'error')
                return
        else:
            self.config[key] = value
            
        if speichere_konfiguration(self.config):
            self.zeige_nachricht(f"✅ Konfiguration gespeichert: {key} = {value}", 'success')
        else:
            self.zeige_nachricht(f"❌ Fehler beim Speichern der Konfiguration", 'error')

    def show_config_dialog(self):
        # Einfacher Konfigurationsdialog
        config_window = tk.Toplevel(self.master)
        config_window.title("Konfiguration")
        config_window.geometry("400x300")
        config_window.configure(bg=self.colors['bg_primary'])
        
        # Konfigurationsoptionen anzeigen
        tk.Label(config_window, text="Aktuelle Konfiguration:", 
                bg=self.colors['bg_primary'], fg='white', font=('Arial', 12, 'bold')).pack(pady=10)
        
        config_text = scrolledtext.ScrolledText(config_window, height=15, width=50)
        config_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        for key, value in self.config.items():
            config_text.insert(tk.END, f"{key} = {value}\n")
        config_text.config(state='disabled')

    def show_menu(self):
        # Kontextmenü anzeigen
        menu = tk.Menu(self.master, tearoff=0)
        menu.add_command(label="📥 Chat beitreten", command=self.join_chat)
        menu.add_command(label="📤 Chat verlassen", command=self.leave_chat)
        menu.add_separator()
        menu.add_command(label="👥 Teilnehmer suchen", command=self.search_participants)
        menu.add_command(label="⚙️ Konfiguration", command=self.show_config_dialog)
        menu.add_separator()
        menu.add_command(label="❓ Hilfe", command=self.show_help)
        menu.add_command(label="🚪 Beenden", command=self.exit_application)
        
        try:
            menu.tk_popup(self.master.winfo_pointerx(), self.master.winfo_pointery())
        finally:
            menu.grab_release()

    def show_help(self):
        help_text = """
🔧 SLCP Chat - Befehle:

/join                - Dem Chat beitreten
/leave               - Chat verlassen
/who                 - Teilnehmer im Netzwerk suchen
/msg <user> <text>   - Nachricht an Nutzer senden
/img <user>          - Bild an Nutzer senden
/set <key> <value>   - Konfiguration ändern und speichern
/exit                - Programm beenden
/help                - Diese Hilfe anzeigen

📝 Tipps:
• Verwende Enter zum Senden
• Klicke auf 📷 um Bilder zu senden
• Klicke auf ⚙️ für das Menü
• Doppelklick auf Teilnehmer für private Nachricht
        """
        self.zeige_nachricht(help_text, 'help')

    def exit_application(self):
        if messagebox.askokcancel("Beenden", "Möchten Sie das Programm wirklich beenden?"):
            if self.is_joined:
                self.leave_chat()
            self.master.quit()

    def empfange_nachrichten(self):
        while True:
            try:
                msg = self.from_network.get(timeout=1)
                self.zeige_nachricht(f"📥 [Empfangen] {msg}", 'received')
                
                # Teilnehmer-Liste aktualisieren (vereinfacht)
                if "JOIN" in msg:
                    user = msg.split()[1] if len(msg.split()) > 1 else "Unbekannt"
                    self.participants.add(user)
                    self.update_participants_list()
                elif "LEAVE" in msg:
                    user = msg.split()[1] if len(msg.split()) > 1 else "Unbekannt"
                    self.participants.discard(user)
                    self.update_participants_list()
                    
            except queue.Empty:
                continue

    def update_participants_list(self):
        self.participants_listbox.delete(0, tk.END)
        for participant in sorted(self.participants):
            self.participants_listbox.insert(tk.END, participant)

    def zeige_nachricht(self, text, msg_type='normal'):
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Farben je nach Nachrichtentyp
        colors = {
            'normal': '#2c3e50',
            'sent': '#27ae60',
            'received': '#3498db',
            'error': '#e74c3c',
            'warning': '#f39c12',
            'success': '#27ae60',
            'info': '#3498db',
            'private': '#9b59b6',
            'image': '#e67e22',
            'auto': '#95a5a6',
            'help': '#34495e'
        }
        
        self.chat_history.config(state='normal')
        
        # Zeitstempel
        self.chat_history.insert(tk.END, f"[{timestamp}] ", 'timestamp')
        
        # Nachricht mit Farbe
        self.chat_history.insert(tk.END, text + "\n", msg_type)
        
        # Text-Tags für Farben konfigurieren
        for tag, color in colors.items():
            self.chat_history.tag_configure(tag, foreground=color)
        
        self.chat_history.tag_configure('timestamp', foreground='#7f8c8d', font=('Arial', 8))
        
        self.chat_history.config(state='disabled')
        self.chat_history.see(tk.END)

def main():
    to_network = queue.Queue()
    from_network = queue.Queue()
    to_discovery = queue.Queue()

    root = tk.Tk()
    app = ChatApp(root, to_network, from_network, to_discovery)
    
    # Schließen-Event abfangen
    root.protocol("WM_DELETE_WINDOW", app.exit_application)
    
    root.mainloop()

if __name__ == "__main__":
    main()
