import socket
import json
import base64
import cv2
import numpy as np
import tkinter as tk
from tkinter import messagebox

# Client configurations
BUFF_SIZE = 65536
SERVER_IP = '192.168.100.27'  # Replace with your server's IP address
PORT = 9999

# Create a UDP client socket
client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, BUFF_SIZE)
server_address = (SERVER_IP, PORT)

# Tkinter App Setup
class VideoStreamingClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Streaming Client")
        self.root.geometry("500x300")

        self.video_list = {}
        self.selected_video = None

        # UI Elements
        self.label = tk.Label(self.root, text="Available Videos:", font=("Arial", 14))
        self.label.pack(pady=10)

        self.video_listbox = tk.Listbox(self.root, width=50, height=10)
        self.video_listbox.pack(pady=10)

        self.play_button = tk.Button(self.root, text="Play Video", command=self.play_video)
        self.play_button.pack(pady=5)

        self.quit_button = tk.Button(self.root, text="Quit", command=self.quit_app)
        self.quit_button.pack(pady=5)

        # Fetch video list
        self.fetch_video_list()

    def fetch_video_list(self):
        """Fetch video list from the server."""
        client_socket.sendto(b"hi", server_address)
        video_list_data = b''

        while True:
            chunk, _ = client_socket.recvfrom(BUFF_SIZE)
            if chunk == b'END':
                break
            video_list_data += chunk

        # Decode the video list
        try:
            self.video_list = json.loads(video_list_data.decode('utf-8'))
            for idx, video in self.video_list.items():
                self.video_listbox.insert(tk.END, f"{idx}: {video}")
        except json.JSONDecodeError as e:
            messagebox.showerror("Error", f"Failed to fetch video list: {e}")

    def play_video(self):
        """Send the selected video to the server and stream it."""
        selected_index = self.video_listbox.curselection()
        if not selected_index:
            messagebox.showwarning("Warning", "Please select a video to play.")
            return

        video_id = int(self.video_listbox.get(selected_index).split(":")[0])
        client_socket.sendto(str(video_id).encode('utf-8'), server_address)

        # Start video streaming in a new window
        self.stream_video()

    def stream_video(self):
        """Stream the selected video from the server."""
        cv2.namedWindow('Video Streaming', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Video Streaming', 800, 600)

        while True:
            try:
                frame_data, _ = client_socket.recvfrom(BUFF_SIZE)
                if frame_data == b'END':
                    print("Video streaming ended.")
                    break

                # Decode and display the frame
                try:
                    frame = base64.b64decode(frame_data)
                    np_data = np.frombuffer(frame, dtype=np.uint8)
                    img = cv2.imdecode(np_data, cv2.IMREAD_COLOR)

                    if img is not None:
                        cv2.imshow('Video Streaming', img)
                        if cv2.waitKey(1) == ord('q'):
                            break
                    else:
                        print("Error decoding frame. Skipping...")
                except Exception as e:
                    print(f"Error processing frame: {e}")
            except socket.timeout:
                print("Socket timeout. Retrying...")
                continue

        cv2.destroyAllWindows()

    def quit_app(self):
        """Close the application."""
        client_socket.close()
        self.root.quit()

# Run the Tkinter application
if __name__ == "__main__":
    root = tk.Tk()
    app = VideoStreamingClient(root)
    root.mainloop()
