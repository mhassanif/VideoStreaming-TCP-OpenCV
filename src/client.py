import socket

def connect_to_server():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(('127.0.0.1', 5000))
    message = client_socket.recv(1024)
    print("Message from server:", message.decode())
    client_socket.close()

connect_to_server()
