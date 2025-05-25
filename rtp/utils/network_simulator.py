# rtp/network_simulator.py
import socket
import threading
import time
import random

class SimulatedNetwork:
    def __init__(self, listen_port, forward_ip, forward_port,
                 drop_rate=0.05, max_delay=0.1, reorder_rate=0.1, duplicate_rate=0.05):
        self.listen_port = listen_port
        self.forward_ip = forward_ip
        self.forward_port = forward_port

        self.drop_rate = drop_rate
        self.max_delay = max_delay
        self.reorder_rate = reorder_rate
        self.duplicate_rate = duplicate_rate

        self.buffer = []
        self.lock = threading.Lock()
        self.running = False

    def start(self):
        self.running = True
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('0.0.0.0', self.listen_port))
        threading.Thread(target=self._recv_loop, daemon=True).start()
        threading.Thread(target=self._forward_loop, daemon=True).start()
        print(f"[Middlebox] Simulated network started on port {self.listen_port} → {self.forward_ip}:{self.forward_port}")

    def _recv_loop(self):
        while self.running:
            data, addr = self.socket.recvfrom(4096)

            # Mô phỏng mất gói
            if random.random() < self.drop_rate:
                print(">> [Drop] Packet dropped")
                continue

            # Mô phỏng trễ gói
            delay = random.uniform(0, self.max_delay)

            # Mô phỏng duplicate
            duplicates = 1 + int(random.random() < self.duplicate_rate)

            for _ in range(duplicates):
                with self.lock:
                    self.buffer.append((time.time() + delay, data))

                # Mô phỏng rối loạn (chèn ngẫu nhiên)
                if random.random() < self.reorder_rate and len(self.buffer) >= 2:
                    i = random.randint(0, len(self.buffer)-1)
                    self.buffer[-1], self.buffer[i] = self.buffer[i], self.buffer[-1]

    def _forward_loop(self):
        send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        while self.running:
            now = time.time()
            with self.lock:
                ready = [pkt for pkt in self.buffer if pkt[0] <= now]
                self.buffer = [pkt for pkt in self.buffer if pkt[0] > now]

            for _, pkt_data in ready:
                send_sock.sendto(pkt_data, (self.forward_ip, self.forward_port))
            time.sleep(0.005)

    def stop(self):
        self.running = False
        self.socket.close()
