#import socket

#def send_message(message, target_ip, target_port=5001):
 #   sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  #  sock.sendto(message.encode(), (target_ip, target_port))
   # print(f"Nachricht gesendet an {target_ip}:{target_port}")
    #sock.close()

#Wird aktuell nicht mehr direkt genutzt, weil wir jetzt alles über Queues regeln. Aber sie zeigt gut, wie einfach UDP in Python funktioniert.“