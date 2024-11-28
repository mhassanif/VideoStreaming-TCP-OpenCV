import socket

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', 5000))
    server_socket.listen(5)
    print("Server listening on port 5000...")
    while True:
        client_socket, addr = server_socket.accept()
        print(f"Connected to {addr}")
        client_socket.sendall(b"Welcome to the video server!")
        client_socket.close()

start_server()
