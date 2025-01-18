import socket
import threading
import time

class RTSPServer:
    def __init__(self, host="127.0.0.1", port=8554, rtp_port=5005):
        self.host = host
        self.port = port
        self.rtp_port = rtp_port
        self.client_address = None
        self.session_id = 123456
        self.state = "INIT"
        self.server_socket = None
        self.rtp_socket = None
        self.running = True

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"RTSP Server listening on {self.host}:{self.port}")

        while self.running:
            client_socket, client_address = self.server_socket.accept()
            print(f"Connection established with {client_address}")
            self.client_address = client_address
            threading.Thread(target=self.handle_client, args=(client_socket,)).start()

    def handle_client(self, client_socket):
        while True:
            try:
                request = client_socket.recv(1024).decode()
                if not request:
                    break
                print("Received RTSP request:\n", request)
                self.process_rtsp_request(request, client_socket)
            except Exception as e:
                print(f"Error handling client: {e}")
                break

        client_socket.close()

    def process_rtsp_request(self, request, client_socket):
        lines = request.split('\n')
        request_type = lines[0].split(' ')[0]

        if request_type == "SETUP":
            self.state = "READY"
            self.send_response(client_socket, 200, setup=True)
        elif request_type == "PLAY":
            if self.state == "READY":
                self.state = "PLAYING"
                self.send_response(client_socket, 200)
                threading.Thread(target=self.send_rtp_packets).start()
        elif request_type == "PAUSE":
            if self.state == "PLAYING":
                self.state = "READY"
                self.send_response(client_socket, 200)
        elif request_type == "TEARDOWN":
            self.state = "INIT"
            self.send_response(client_socket, 200)
            self.running = False

    def send_response(self, client_socket, code, setup=False):
        response = f"RTSP/1.0 {code} OK\r\n"
        response += f"CSeq: 1\r\n"
        if setup:
            response += f"Session: {self.session_id}\r\n"
        response += "\r\n"
        client_socket.send(response.encode())

    def send_rtp_packets(self):
        self.rtp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        with open("video.data", "rb") as video_file:
            while self.state == "PLAYING":
                data = video_file.read(1024)  # Simulate a packet
                if not data:
                    break
                self.rtp_socket.sendto(data, (self.client_address[0], self.rtp_port))
                time.sleep(0.05)  # Simulate 20 FPS
        self.rtp_socket.close()

if __name__ == "__main__":
    server = RTSPServer()
    server.start()
