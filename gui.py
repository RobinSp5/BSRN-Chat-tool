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

        # Load configuration
        try:
            self.config = toml.load(config_path)
        except Exception:
            messagebox.showwarning("Config Warning", f"Fehler beim Laden der Konfiguration: {config_path}\nVerwende Standardwerte.")
            self.config = {
                'network': {
                    'discovery_port': 12345,
                    'chat_port': 0,
                    'broadcast_address': '255.255.255.255',
                    'discovery_interval': 5
                },
                'user': {
                    'default_username': 'ChatUser',
                    'max_message_length': 1024,
                    'max_image_size': 1048576
                },
                'system': {
                    'socket_timeout': 5,
                    'worker_threads': 2,
                    'log_level': 'INFO'
                }
            }

        # Username
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

        # Welcome message
        self.msg_display.configure(state='normal')
        self.msg_display.insert(tk.END, f"Willkommen {self.username}!\n")
        self.msg_display.insert(tk.END, "Verwende 'Hilfe' im Menü für verfügbare Befehle.\n\n")
        self.msg_display.configure(state='disabled')

        # Poll for new messages and user list
        self.after(100, self._poll_messages)
        self.after(5000, self._update_user_list)

    def _build_menu(self):
        menubar = tk.Menu(self)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Beenden", command=self.on_close)
        menubar.add_cascade(label="Datei", menu=filemenu)

        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="Befehle", command=self.show_help)
        menubar.add_cascade(label="Hilfe", menu=helpmenu)

        self.config(menu=menubar)

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
        img_btn = tk.Button(entry_frame, text="Bild senden", command=self.send_image)
        img_btn.pack(side=tk.LEFT, padx=(5,0))
        refresh_btn = tk.Button(entry_frame, text="Aktualisieren", command=self._update_user_list)
        refresh_btn.pack(side=tk.LEFT, padx=(5,0))

    def _poll_messages(self):
        msg = self.ipc.get_message(timeout=0)
        while msg:
            self._display_message(msg)
            msg = self.ipc.get_message(timeout=0)
        self.after(100, self._poll_messages)

    def _update_user_list(self):
        self.discovery.request_discovery()
        users = self.ipc.get_active_users()
        self.user_listbox.delete(0, tk.END)
        for username, info in users.items():
            ip = info.get('ip')
            port = info.get('tcp_port')
            last = time.strftime('%H:%M:%S', time.localtime(info.get('last_seen', time.time())))
            self.user_listbox.insert(tk.END, f"{username} @ {ip}:{port} (zuletzt {last})")

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
            if success:
                self._display_message({'type':'text','sender':f'Du → {key}','content':text,'timestamp':time.time()})
        else:
            successful, total = self.chat_client.broadcast_message(users, text, msg_type='text')
            self._display_message({'type':'system','sender':'System', 'content':f'Nachricht an {successful} von {total} Nutzern gesendet.', 'timestamp':time.time()})
        self.entry.delete(0, tk.END)

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

if __name__ == '__main__':
    app = ChatGUI()
    app.mainloop()
