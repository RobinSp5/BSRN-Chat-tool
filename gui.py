import tkinter as tk
from tkinter import scrolledtext, filedialog, simpledialog, messagebox
import threading
import time
import os
import base64
import json
import toml

from ipc_handler import IPCHandler
from chat_server import ChatServer
from discovery import DiscoveryService
from chat_client import ChatClient

class ChatGUI(tk.Tk):
    def __init__(self, config_path="config.toml", username=None):
        super().__init__()
        self.title("Simple LAN Chat (GUI)")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Menü leiste
        self._build_menu()

        # Konfigurationsdatei laden
        try:
            self.config = toml.load(config_path)
        except Exception as e:
            messagebox.showerror("Konfigurationsfehler", f"Die Konfigurationsdatei '{config_path}' konnte nicht geladen werden.\n\nFehler: {str(e)}\n\nDas Programm wird beendet.")
            self.destroy()
            return

        # Nutzername abfrage zu Beginn des Programms
        self.username = username or simpledialog.askstring("Username", "Gib deinen Nutzernamen ein:")
        if not self.username:
            self.username = self.config['user']['default_username']

        # Setup IPC, Server, Discovery, Client
        self.ipc = IPCHandler()
        self.chat_server = ChatServer(self.config, self.ipc)
        self.chat_server.start()
        chat_port = self.config['network']['chat_port']

        self.discovery = DiscoveryService(self.config, self.ipc, self.username, chat_port)
        self.discovery.start()

        self.chat_client = ChatClient(self.config, self.username)

        # Build UI
        self._build_widgets()

        # Willkommensnachricht zu Beginn
        self.msg_display.configure(state='normal')
        self.msg_display.insert(tk.END, f"Willkommen {self.username}!\n")
        self.msg_display.insert(tk.END, "Verwende 'Hilfe' im Menü für verfügbare Befehle.\n\n")
        self.msg_display.configure(state='disabled')

        # Poll for new messages and user list
        self.after(100, self._poll_messages)
        self.after(3000, self._update_user_list)  # Geändert von 5000 auf 3000 (3 Sekunden)

    # Erstellt die Menüleiste mit Datei- und Hilfemenü
    def _build_menu(self):
        menubar = tk.Menu(self)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Beenden", command=self.on_close)
        menubar.add_cascade(label="Datei", menu=filemenu)

        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="Befehle", command=self.show_help)
        menubar.add_cascade(label="Hilfe", menu=helpmenu)

        self.config(menu=menubar)

    # Zeigt eine Hilfemeldung mit verfügbaren Befehlen
    def show_help(self):
        help_text = (
            "Verfügbare Befehle:\n"
            "/help             - Hilfe anzeigen\n"
            "/who oder Aktualisieren - Aktive Nutzer anzeigen\n"
            "/msg <Nachricht>  - Nachricht an alle senden\n"
            "/pm <Nutzer> <Nachricht> - Private Nachricht senden\n"
            "/img <Pfad>       - Bild an alle senden\n"
            "/quit oder Schließen   - Programm beenden\n"
        )
        messagebox.showinfo("Hilfe", help_text)

    # Erstellt die GUI-Widgets
    def _build_widgets(self):
        user_frame = tk.Frame(self)
        user_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        tk.Label(user_frame, text="Aktive Nutzer").pack()
        self.user_listbox = tk.Listbox(user_frame, width=25)
        self.user_listbox.pack(fill=tk.Y, expand=True)

        msg_frame = tk.Frame(self)
        msg_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        tk.Label(msg_frame, text="Chatverlauf").pack()
        self.msg_display = scrolledtext.ScrolledText(msg_frame, state='disabled', wrap=tk.WORD)
        self.msg_display.pack(fill=tk.BOTH, expand=True)

        entry_frame = tk.Frame(self)
        entry_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        self.entry = tk.Entry(entry_frame)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
        self.entry.bind('<Return>', lambda e: self.send_text())
        send_btn = tk.Button(entry_frame, text="Senden", command=self.send_text)
        send_btn.pack(side=tk.LEFT)
        dm_btn = tk.Button(entry_frame, text="Direct Message", command=self.send_direct_message)
        dm_btn.pack(side=tk.LEFT, padx=(5,0))
        img_btn = tk.Button(entry_frame, text="Bild senden", command=self.send_image)
        img_btn.pack(side=tk.LEFT, padx=(5,0))
        refresh_btn = tk.Button(entry_frame, text="Aktualisieren", command=self._update_user_list)
        refresh_btn.pack(side=tk.LEFT, padx=(5,0))

    # Sendet eine Direkt Nachricht an einen ausgewählten User
    def send_direct_message(self):
        """Sendet eine Direct Message an einen ausgewählten User"""
        text = self.entry.get().strip()
        if not text:
            messagebox.showwarning("Warnung", "Bitte gib eine Nachricht ein!")
            return
            
        users = self.ipc.get_active_users()
        if not users:
            messagebox.showwarning("Warnung", "Keine aktiven Nutzer gefunden!")
            return
            
        # User-Auswahl mit Listbox-Dialog
        selected_user = self._show_user_selection_dialog(list(users.keys()))
        
        if not selected_user or selected_user not in users:
            return  # User hat abgebrochen oder ungültigen User ausgewählt
            
        # Direct Message senden
        success = self.chat_client.send_to_user(selected_user, users, text, msg_type='text')
        if success:
            self._display_message({'type':'text','sender':f'Du → {selected_user}','content':text,'timestamp':time.time()})
            messagebox.showinfo("Erfolg", f"Direct Message an {selected_user} gesendet!")
        else:
            messagebox.showerror("Fehler", f"Fehler beim Senden an {selected_user}!")
            
        self.entry.delete(0, tk.END)

    # Zeigt einen Dialog zur Auswahl eines Users für Direct Messages
    def _show_user_selection_dialog(self, user_names):
        """Zeigt einen Dialog mit Listbox zur User-Auswahl"""
        dialog = tk.Toplevel(self)
        dialog.title("User auswählen")
        dialog.geometry("300x200")
        dialog.transient(self)
        dialog.grab_set()
        
        # Zentrieren des Dialogs
        dialog.geometry("+%d+%d" % (self.winfo_rootx() + 50, self.winfo_rooty() + 50))
        
        selected_user = None
        
        tk.Label(dialog, text="Wähle einen User für die Direct Message:").pack(pady=10)
        
        # Listbox mit Usern
        listbox_frame = tk.Frame(dialog)
        listbox_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        listbox = tk.Listbox(listbox_frame)
        scrollbar = tk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)
        
        for user in user_names:
            listbox.insert(tk.END, user)
        
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Buttons
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)
        
        def on_select():
            nonlocal selected_user
            selection = listbox.curselection()
            if selection:
                selected_user = user_names[selection[0]]
                dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        # Doppelklick auf Listbox
        listbox.bind('<Double-Button-1>', lambda e: on_select())
        
        tk.Button(button_frame, text="Auswählen", command=on_select).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Abbrechen", command=on_cancel).pack(side=tk.LEFT, padx=5)
        
        # Warten bis Dialog geschlossen wird
        dialog.wait_window()
        
        return selected_user

    #Fragt regelmäßig über IPCHandler.get_message() neue eingehende Nachrichten ab und zeigt sie über _display_message() an.
    def _poll_messages(self):
        msg = self.ipc.get_message(timeout=0)
        while msg:
            self._display_message(msg)
            msg = self.ipc.get_message(timeout=0)
        self.after(100, self._poll_messages)

    # Aktualisiert die Liste der aktiven Nutzer alle 3 Sekunden
    def _update_user_list(self):
        self.discovery.request_discovery()
        users = self.ipc.get_active_users()
        self.user_listbox.delete(0, tk.END)
        for username, info in users.items():
            ip = info.get('ip')
            port = info.get('tcp_port')
            last = time.strftime('%H:%M:%S', time.localtime(info.get('last_seen', time.time())))
            self.user_listbox.insert(tk.END, f"{username} @ {ip}:{port} (zuletzt {last})")
        
        # Automatisch alle 3 Sekunden wiederholen
        self.after(3000, self._update_user_list)

    # Zeigt eine Nachricht im Chatverlauf an
    # Unterscheidet zwischen Text, Bild und Systemnachrichten
    def _display_message(self, message):
        t = time.strftime('%H:%M:%S', time.localtime(message.get('timestamp', time.time())))
        sender = message.get('sender', 'Unknown')
        mtype = message.get('type')
        content = message.get('content', '')

        self.msg_display.configure(state='normal')
        if mtype == 'text':
            self.msg_display.insert(tk.END, f"[{t}] {sender}: {content}\n")
        elif mtype == 'image':
            fname = message.get('filename', 'image')
            try:
                data = base64.b64decode(message.get('image_data', ''))
                safe_fname = f"{sender}_{fname}"
                with open(safe_fname, 'wb') as f:
                    f.write(data)
                self.msg_display.insert(tk.END, f"[{t}] {sender} hat ein Bild gesendet: {safe_fname}\n")
            except Exception as e:
                self.msg_display.insert(tk.END, f"[{t}] Fehler beim Speichern des Bildes: {e}\n")
        else:
            self.msg_display.insert(tk.END, f"[{t}] {sender}: {message.get('content', '')}\n")
        self.msg_display.see(tk.END)
        self.msg_display.configure(state='disabled')

    # Sendet eine Textnachricht an den ausgewählten Nutzer oder an alle
    # und zeigt die eigene Nachricht im Chatverlauf an.
    def send_text(self):
        text = self.entry.get().strip()
        if not text:
            return
        users = self.ipc.get_active_users()
        sel = self.user_listbox.curselection()
        if sel:
            idx = sel[0]
            key = list(users.keys())[idx]
            success = self.chat_client.send_to_user(key, users, text, msg_type='text')
            # Zeige eigene Nachricht im Chatverlauf
            self._display_message({'type':'text','sender':f'Du → {key}','content':text,'timestamp':time.time()})
        else:
            successful, total = self.chat_client.broadcast_message(users, text, msg_type='text')
            # Zeige eigene Nachricht im Chatverlauf
            self._display_message({'type':'text','sender':'Du','content':text,'timestamp':time.time()})
            self._display_message({'type':'system','sender':'System', 'content':f'Nachricht an {successful} von {total} Nutzern gesendet.', 'timestamp':time.time()})
        self.entry.delete(0, tk.END)

    # Sendet ein Bild an den ausgewählten Nutzer oder an alle
    # und zeigt eine Bestätigung im Chatverlauf an.
    # Das Bild wird über einen Dateiauswahldialog ausgewählt.
    def send_image(self):
        path = filedialog.askopenfilename(title="Bild auswählen", filetypes=[("Bilddateien", "*.png;*.jpg;*.jpeg;*.gif")])
        if not path or not os.path.exists(path):
            return
        users = self.ipc.get_active_users()
        sel = self.user_listbox.curselection()
        if sel:
            idx = sel[0]
            key = list(users.keys())[idx]
            info = users[key]
            if self.chat_client.send_image_message(info.get('ip'), info.get('tcp_port'), path):
                self._display_message({'type':'system','sender':'System','content':f'Bild an {key} gesendet.','timestamp':time.time()})
        else:
            sent = 0
            for username, info in users.items():
                ip = info.get('ip')
                port = info.get('tcp_port')
                if ip and port and self.chat_client.send_image_message(ip, port, path):
                    sent += 1
            total = len(users)
            self._display_message({'type':'system','sender':'System','content':f'Bild an {sent} von {total} Nutzern gesendet.', 'timestamp':time.time()})

    def on_close(self):
        users = self.ipc.get_active_users()
        if users:
            self.chat_client.broadcast_message(users, f"{self.username} hat den Chat verlassen.", msg_type='system')
        self.chat_server.stop()
        self.discovery.stop()
        self.destroy()

# Hauptprogrammstart
if __name__ == '__main__':
    app = ChatGUI()
    app.mainloop()
