import socket
import threading
import time
import wave
from rtp.packet import RTPPacket

class RTPReceiver:
    def __init__(self, bind_ip, bind_port):
        self.bind_ip = bind_ip
        self.bind_port = bind_port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((bind_ip, bind_port))
        self.running = False
        self.audio_writer = None
        self.stats = {
            'packets_received': 0,
            'last_seq': None,
            'lost_packets': 0,
            'out_of_order': 0
        }
    
    def start_receiving(self):
        """Bắt đầu luồng nhận gói tin RTP"""
        self.audio_writer = wave.open("received.wav", "wb")
        self.audio_writer.setnchannels(1)
        self.audio_writer.setsampwidth(2)
        self.audio_writer.setframerate(8000)
        self.running = True
        self.receiver_thread = threading.Thread(target=self._receiver_loop)
        self.receiver_thread.daemon = True
        self.receiver_thread.start()
        print(f"Receiver started on {self.bind_ip}:{self.bind_port}")
    
    def stop_receiving(self):
        """Dừng luồng nhận gói tin"""
        self.running = False
        if hasattr(self, 'receiver_thread'):
            self.socket.close()
            self.audio_writer.close()
            self.receiver_thread.join(timeout=1.0)
    
    def _receiver_loop(self):
        """Vòng lặp nhận gói tin"""
        self.socket.settimeout(1.0)  # Timeout 1 giây
        
        while self.running:
            try:
                # Nhận gói tin
                packet_bytes, addr = self.socket.recvfrom(2048)
                
                # Giải mã gói RTP
                try:
                    rtp_packet = RTPPacket.decode(packet_bytes)
                    self._process_packet(rtp_packet, addr)
                except Exception as e:
                    print(f"Error decoding RTP packet: {e}")
            
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Error in receiver loop: {e}")
                if not self.running:
                    break
        
        print("Receiver stopped")
    
    def _process_packet(self, packet, addr):
        """Xử lý gói tin RTP nhận được"""
        self.stats['packets_received'] += 1
        
        # Kiểm tra thứ tự gói tin
        if self.stats['last_seq'] is not None:
            expected_seq = (self.stats['last_seq'] + 1) % 65536
            if packet.seq_num != expected_seq:
                if ((packet.seq_num < expected_seq and not (expected_seq > 60000 and packet.seq_num < 5000)) or
                    (expected_seq < 5000 and packet.seq_num > 60000)):
                    # Gói tin đến trễ hoặc không đúng thứ tự
                    self.stats['out_of_order'] += 1
                else:
                    # Gói tin bị mất
                    if packet.seq_num > expected_seq:
                        self.stats['lost_packets'] += (packet.seq_num - expected_seq)
                    else:  # Trường hợp số thứ tự quay vòng
                        self.stats['lost_packets'] += (65536 - expected_seq + packet.seq_num)
        
        self.stats['last_seq'] = packet.seq_num
        
        # In thông tin gói tin
        print(f"Received from {addr}: {packet}")
        
        if self.audio_writer:
            self.audio_writer.writeframes(packet.payload)
        loss_rate = self.stats['lost_packets'] / (self.stats['packets_received'] + self.stats['lost_packets']) * 100 if (self.stats['packets_received'] + self.stats['lost_packets']) > 0 else 0
        print(f"Stats: Received={self.stats['packets_received']}, Lost={self.stats['lost_packets']}, Out-of-order={self.stats['out_of_order']}, Loss Rate={loss_rate:.2f}%")