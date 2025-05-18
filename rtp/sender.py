import socket
import threading
import time
import random
import wave
from rtp.packet import RTPPacket

class RTPSender:
    def __init__(self, dest_ip, dest_port, payload_type=96, ssrc=None):
        self.dest_ip = dest_ip
        self.dest_port = dest_port
        self.payload_type = payload_type
        self.seq_num = random.randint(0, 65535)  # Bắt đầu với số ngẫu nhiên
        self.timestamp = random.randint(0, 2**32-1)
        self.ssrc = ssrc if ssrc else random.randint(0, 2**32-1)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.running = False
        self.timestamp_increment = 160  # Tăng mỗi gói (ví dụ cho 20ms audio @ 8kHz)
        self.audio_file = None

    def set_audio_file(self, wav_path):
        self.audio_file = wave.open(wav_path, "rb")
        assert self.audio_file.getnchannels() == 1
        assert self.audio_file.getframerate() == 8000
        assert self.audio_file.getsampwidth() == 2
    
    def send_packet(self, payload):
        """Gửi một gói tin RTP với payload được cung cấp"""
        packet = RTPPacket(
            payload_type=self.payload_type,
            seq_num=self.seq_num,
            timestamp=self.timestamp,
            ssrc=self.ssrc,
            payload=payload
        )
        
        # Đóng gói và gửi
        packet_bytes = packet.encode()
        self.socket.sendto(packet_bytes, (self.dest_ip, self.dest_port))
        
        print(f"Sent: {packet}")
        
        # Cập nhật số thứ tự và timestamp
        self.seq_num = (self.seq_num + 1) % 65536
        self.timestamp = (self.timestamp + self.timestamp_increment) % (2**32)
        
        return packet
    
    def start_sending(self, interval=0.02, duration=None):
        """Bắt đầu luồng gửi gói tin RTP theo chu kỳ
        
        Args:
            interval: Khoảng thời gian giữa các gói tin (giây)
            duration: Thời gian chạy (giây), None để chạy vô hạn
        """
        self.running = True
        self.sender_thread = threading.Thread(target=self._sender_loop, args=(interval, duration))
        self.sender_thread.daemon = True
        self.sender_thread.start()
    
    def stop_sending(self):
        """Dừng luồng gửi gói tin"""
        self.running = False
        if hasattr(self, 'sender_thread'):
            self.sender_thread.join(timeout=1.0)
    
    def _sender_loop(self, interval, duration):
        start_time = time.time()
        packet_count = 0
        while self.running:
            if self.audio_file:
                frame = self.audio_file.readframes(160)
                if not frame:
                    break
                payload = frame
            else:
                payload = f"Packet {packet_count} data".encode()
            self.send_packet(payload)
            packet_count += 1
            if duration and (time.time() - start_time) >= duration:
                break
            time.sleep(interval)
        self.running = False
        print(f"Sender stopped after {packet_count} packets")