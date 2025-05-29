"""
Discovery Service für automatische Nutzererkennung im LAN
Verwendet UDP Broadcast für Peer-Discovery
"""

import socket
import threading
import time
import json
from typing import Dict, Any

class DiscoveryService:
    def __init__(self, config: Dict[str, Any], ipc_handler, username: str):
        self.config = config
        self.ipc_handler = ipc_handler
        self.username = username
        self.running = False
        
        # UDP Socket für Discovery
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.settimeout(1)
        
        # Eigene IP-Adresse ermitteln
        self.local_ip = self.get_local_ip()
        
    def get_local_ip(self):
        """Lokale IP-Adresse ermitteln"""
        try:
            # Dummy-Verbindung aufbauen um lokale IP zu finden
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except:
            return "127.0.0.1"
            
    def start(self):
        """Discovery Service starten"""
        self.running = True
        
        # Listener-Thread für eingehende Discovery-Nachrichten
        listener_thread = threading.Thread(target=self.listen_for_discoveries)
        listener_thread.daemon = True
        listener_thread.start()
        
        # Broadcaster-Thread für ausgehende Discovery-Nachrichten
        broadcast_thread = threading.Thread(target=self.broadcast_presence)
        broadcast_thread.daemon = True
        broadcast_thread.start()
        
    def stop(self):
        """Discovery Service stoppen"""
        self.running = False
        self.sock.close()
        
    def listen_for_discoveries(self):
        """Auf Discovery-Nachrichten hören"""
        # Listener Socket erstellen
        listener_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        listener_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Für Windows: SO_REUSEPORT-Alternative
        try:
            listener_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except AttributeError:
            pass  # SO_REUSEPORT ist nicht auf allen Systemen verfügbar
        listener_sock.settimeout(1)
        
        try:
            # An Discovery Port binden - mit SO_REUSEADDR für mehrere Instanzen
            listener_sock.bind(('', self.config['network']['discovery_port']))
            
            while self.running:
                try:
                    # Discovery-Nachricht empfangen
                    data, addr = listener_sock.recvfrom(1024)
                    message = json.loads(data.decode('utf-8'))
                    
                    # Eigene Nachrichten ignorieren (aber nur wenn auch der Username identisch ist)
                    if message.get('type') == 'discovery' and message.get('username') != self.username:
                        # Nutzer zur aktiven Liste hinzufügen
                        username = message.get('username', 'Unknown')
                        self.ipc_handler.update_user_list(username, addr[0])
                        
                        # Response senden wenn es ein Request war
                        if message.get('action') == 'request':
                            self.send_discovery_response(addr[0])
                            
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"Discovery Listener Error: {e}")
                    
        except Exception as e:
            print(f"Discovery Bind Error: {e}")
        finally:
            listener_sock.close()
            
    def broadcast_presence(self):
        """Eigene Präsenz im Netzwerk bekannt geben"""
        while self.running:
            try:
                # Discovery-Nachricht erstellen
                discovery_msg = {
                    'type': 'discovery',
                    'action': 'announce',
                    'username': self.username,
                    'ip': self.local_ip,
                    'timestamp': time.time()
                }
                
                # Nachricht als JSON serialisieren
                message = json.dumps(discovery_msg).encode('utf-8')
                
                # Broadcast senden
                broadcast_addr = self.config['network']['broadcast_address']
                discovery_port = self.config['network']['discovery_port']
                self.sock.sendto(message, (broadcast_addr, discovery_port))
                
                # Warten bis zum nächsten Broadcast
                time.sleep(self.config['network']['discovery_interval'])
                
            except Exception as e:
                print(f"Broadcast Error: {e}")
                time.sleep(5)  # Bei Fehler kurz warten
                
    def send_discovery_response(self, target_ip: str):
        """Discovery-Response an spezifische IP senden"""
        try:
            response_msg = {
                'type': 'discovery',
                'action': 'response',
                'username': self.username,
                'ip': self.local_ip,
                'timestamp': time.time()
            }
            
            message = json.dumps(response_msg).encode('utf-8')
            discovery_port = self.config['network']['discovery_port']
            self.sock.sendto(message, (target_ip, discovery_port))
            
        except Exception as e:
            print(f"Discovery Response Error: {e}")
            
    def request_discovery(self):
        """Aktive Discovery-Anfrage senden"""
        try:
            request_msg = {
                'type': 'discovery',
                'action': 'request',
                'username': self.username,
                'ip': self.local_ip,
                'timestamp': time.time()
            }
            
            message = json.dumps(request_msg).encode('utf-8')
            broadcast_addr = self.config['network']['broadcast_address']
            discovery_port = self.config['network']['discovery_port']
            self.sock.sendto(message, (broadcast_addr, discovery_port))
            
        except Exception as e:
            print(f"Discovery Request Error: {e}")
