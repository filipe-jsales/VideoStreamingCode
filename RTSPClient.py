import socket
import threading

class RTSPClient:
    def __init__(self, server_address, server_port, rtp_port):
        self.server_address = server_address
        self.server_port = server_port
        self.rtp_port = rtp_port
        self.rtsp_socket = None
        self.session_id = None
        self.cseq = 1
        self.is_playing = False
        self.rtp_socket = None

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

    def setup(self, filename):
        self.rtp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rtp_socket.settimeout(0.5)
        request = (f"SETUP {filename} RTSP/1.0\r\n"
                   f"CSeq: {self.cseq}\r\n"
                   f"Transport: RTP/UDP; client_port= {self.rtp_port}\r\n\r\n")
        response = self.send_rtsp_request(request)
        self.parse_response(response)
        self.cseq += 1

    def play(self):
        if not self.session_id:
            print("Error: Session not set up.")
            return
        request = (f"PLAY RTSP/1.0\r\n"
                   f"CSeq: {self.cseq}\r\n"
                   f"Session: {self.session_id}\r\n\r\n")
        response = self.send_rtsp_request(request)
        self.cseq += 1
        self.is_playing = True

    def pause(self):
        if not self.session_id:
            print("Error: Session not set up.")
            return
        request = (f"PAUSE RTSP/1.0\r\n"
                   f"CSeq: {self.cseq}\r\n"
                   f"Session: {self.session_id}\r\n\r\n")
        response = self.send_rtsp_request(request)
        self.cseq += 1
        self.is_playing = False

    def teardown(self):
        if not self.session_id:
            print("Error: Session not set up.")
            return
        request = (f"TEARDOWN RTSP/1.0\r\n"
                   f"CSeq: {self.cseq}\r\n"
                   f"Session: {self.session_id}\r\n\r\n")
        response = self.send_rtsp_request(request)
        self.cseq += 1
        self.rtsp_socket.close()
        self.rtp_socket.close()
        self.is_playing = False

    def receive_rtp_packets(self):
        while self.is_playing:
            try:
                data, _ = self.rtp_socket.recvfrom(2048)
                print("Received RTP packet:", data)
            except socket.timeout:
                continue

if __name__ == "__main__":
    server_address = "127.0.0.1"
    server_port = 8554
    rtp_port = 5005

    client = RTSPClient(server_address, server_port, rtp_port)
    client.connect()

    filename = "video.mp4"
    client.setup(filename)

    client.play()

    rtp_thread = threading.Thread(target=client.receive_rtp_packets)
    rtp_thread.start()

    input("Press Enter to pause...\n")
    client.pause()

    input("Press Enter to teardown...\n")
    client.teardown()
    rtp_thread.join()