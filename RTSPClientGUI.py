import socket
import threading
import tkinter as tk
from tkinter import messagebox
import cv2
import numpy as np

class RTSPClientGUI:
    def __init__(self, root, server_address, server_port, rtp_port):
        self.server_address = server_address
        self.server_port = server_port
        self.rtp_port = rtp_port
        self.rtsp_socket = None
        self.rtp_socket = None
        self.session_id = None
        self.cseq = 1
        self.is_playing = False
        self.video_thread = None
        self.running = True

        self.root = root
        self.root.title("RTSP Video Client")

        self.video_label = tk.Label(root)
        self.video_label.pack()

        self.setup_button = tk.Button(root, text="SETUP", command=self.setup)
        self.setup_button.pack(side=tk.LEFT)

        self.play_button = tk.Button(root, text="PLAY", command=self.play)
        self.play_button.pack(side=tk.LEFT)

        self.pause_button = tk.Button(root, text="PAUSE", command=self.pause)
        self.pause_button.pack(side=tk.LEFT)

        self.teardown_button = tk.Button(root, text="TEARDOWN", command=self.teardown)
        self.teardown_button.pack(side=tk.LEFT)

    def connect(self):
        self.rtsp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.rtsp_socket.connect((self.server_address, self.server_port))

    def send_rtsp_request(self, request):
        self.rtsp_socket.send(request.encode())
        response = self.rtsp_socket.recv(1024).decode()
        print("RTSP Response:\n", response)
        return response

    def parse_response(self, response):
        for line in response.split('\n'):
            if line.startswith("Session"):
                self.session_id = line.split(':')[1].strip()

    def setup(self):
        print(f"Cliente configurado para receber RTP na porta {self.rtp_port}")
        self.rtp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rtp_socket.bind(("0.0.0.0", self.rtp_port))  # Aceita pacotes em todas as interfaces
        self.rtp_socket.settimeout(0.5)
        request = (f"SETUP video RTSP/1.0\r\n"
                f"CSeq: {self.cseq}\r\n"
                f"Transport: RTP/UDP; client_port= {self.rtp_port}\r\n\r\n")
        response = self.send_rtsp_request(request)
        if "Session" not in response:
            print("Erro ao configurar sessão RTSP.")
            return
        self.parse_response(response)
        print(f"RTP configurado na porta: {self.rtp_port}")
        self.cseq += 1

    def play(self):
        if not self.session_id:
            messagebox.showerror("Error", "Session not set up.")
            return

        request = (f"PLAY RTSP/1.0\r\n"
                   f"CSeq: {self.cseq}\r\n"
                   f"Session: {self.session_id}\r\n\r\n")
        response = self.send_rtsp_request(request)
        self.cseq += 1
        self.is_playing = True

        self.video_thread = threading.Thread(target=self.receive_rtp_packets)
        self.video_thread.start()

    def pause(self):
        if not self.session_id:
            messagebox.showerror("Error", "Session not set up.")
            return

        request = (f"PAUSE RTSP/1.0\r\n"
                   f"CSeq: {self.cseq}\r\n"
                   f"Session: {self.session_id}\r\n\r\n")
        response = self.send_rtsp_request(request)
        self.cseq += 1
        self.is_playing = False

    def teardown(self):
        if not self.session_id:
            messagebox.showerror("Error", "Session not set up.")
            return

        request = (f"TEARDOWN RTSP/1.0\r\n"
                   f"CSeq: {self.cseq}\r\n"
                   f"Session: {self.session_id}\r\n\r\n")
        response = self.send_rtsp_request(request)
        self.cseq += 1
        self.rtsp_socket.close()
        self.rtp_socket.close()
        self.is_playing = False
        self.running = False

    def receive_rtp_packets(self):
        print(f"Recebendo dados {self.server_address}:{self.server_port}")
        while self.running and self.is_playing:
            try:
                data, _ = self.rtp_socket.recvfrom(65536)
                print("Pacote RTP recebido.")
                frame = np.frombuffer(data, dtype=np.uint8)
                frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)

                if frame is not None:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frame = cv2.resize(frame, (640, 480))

                    img_tk = tk.PhotoImage(master=self.root, image=tk.PhotoImage(data=frame))
                    self.video_label.configure(image=img_tk)
                    self.video_label.image = img_tk
            except socket.timeout:
                print("Timeout: Nenhum pacote recebido.")

if __name__ == "__main__":
    root = tk.Tk()
    client = RTSPClientGUI(root, server_address="127.0.0.1", server_port=8554, rtp_port=5005)
    client.connect()
    root.mainloop()
