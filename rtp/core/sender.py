import socket
import threading
import time
import random
import wave
from rtp.core.packet import RTPPacket
from rtp.utils.fec import FECHandler
from rtp.utils.retransmission import RetransmissionHandler

class RTPSender:
    def __init__(self, dest_ip, dest_port, payload_type=RTPPacket.PT_AUDIO, ssrc=None, initial_seq_num=0, group_size=4):
        self.dest_ip = dest_ip
        self.dest_port = dest_port
        self.payload_type = payload_type
        self.seq_num = initial_seq_num
        self.timestamp = 0
        self.ssrc = ssrc if ssrc else random.randint(0, 2**32-1)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.running = False
        self.timestamp_increment = 160  # Tăng mỗi gói (ví dụ cho 20ms audio @ 8kHz)
        self.audio_file = None
        
        # For packet retransmission
        self.packet_history = {}  # Store recent packets for retransmission
        self.history_size = 1000  # Number of packets to keep in history
        self.lock = threading.Lock()  # For thread-safe access to packet history
        
        self.fec_handler = FECHandler(group_size=group_size)
        self.rtx_handler = RetransmissionHandler()

    def set_audio_file(self, wav_path):
        self.audio_file = wave.open(wav_path, "rb")
        assert self.audio_file.getnchannels() == 1
        assert self.audio_file.getframerate() == 8000
        assert self.audio_file.getsampwidth() == 2
    
    def create_packet(self, payload, payload_type=RTPPacket.PT_AUDIO):
        """Create a new RTP packet"""
        packet = RTPPacket(
            payload_type=payload_type,
            seq_num=self.seq_num,
            timestamp=self.timestamp,
            ssrc=self.ssrc,
            payload=payload
        )
        self.seq_num += 1
        self.timestamp += len(payload)  # Simple timestamp increment
        return packet
        
    def process_packet(self, packet):
        """Process packet before sending, including FEC and retransmission handling"""
        # Store packet for potential retransmission
        self.rtx_handler.add_packet(packet)
        
        # Generate FEC packet if group is complete
        fec_packet = self.fec_handler.add_packet(packet)
        
        packets_to_send = [packet]
        if fec_packet:
            packets_to_send.append(fec_packet)
            
        return packets_to_send
        
    def handle_nack(self, nack_packet):
        """Handle NACK packet and return retransmission packets"""
        return self.rtx_handler.handle_nack(nack_packet)
    
    def send_audio(self, audio_data, chunk_size=1024):
        """Send audio data in chunks"""
        packets = []
        
        # Split audio data into chunks
        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i:i + chunk_size]
            packet = self.create_packet(chunk)
            processed_packets = self.process_packet(packet)
            packets.extend(processed_packets)
            
        return packets
    
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
        
        # Store packet for potential retransmission
        with self.lock:
            self.packet_history[self.seq_num] = packet_bytes
            # Remove old packets if history is too large
            if len(self.packet_history) > self.history_size:
                oldest_seq = min(self.packet_history.keys())
                del self.packet_history[oldest_seq]
        
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
        # Start sender thread
        self.sender_thread = threading.Thread(target=self._sender_loop, args=(interval, duration))
        self.sender_thread.daemon = True
        self.sender_thread.start()
        
        # Start NACK listener thread
        self.nack_thread = threading.Thread(target=self._nack_listener)
        self.nack_thread.daemon = True
        self.nack_thread.start()
    
    def stop_sending(self):
        """Dừng luồng gửi gói tin"""
        self.running = False
        if hasattr(self, 'sender_thread'):
            self.sender_thread.join(timeout=1.0)
        if hasattr(self, 'nack_thread'):
            self.nack_thread.join(timeout=1.0)
    
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

    def _nack_listener(self):
        """Listen for and handle NACK packets"""
        self.socket.settimeout(0.1)  # 100ms timeout
        while self.running:
            try:
                data, addr = self.socket.recvfrom(2048)
                try:
                    packet = RTPPacket.decode(data)
                    if packet.payload_type == RTPPacket.PT_NACK:
                        self._handle_nack(packet, addr)
                except Exception as e:
                    print(f"Error processing NACK: {e}")
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"Error in NACK listener: {e}")
    
    def _handle_nack(self, nack_packet, addr):
        """Handle NACK packet by retransmitting requested packets"""
        missing_seq_nums = nack_packet.get_nack_sequence_numbers()
        print(f"Received NACK for sequences: {missing_seq_nums}")
        
        with self.lock:
            for seq_num in missing_seq_nums:
                if seq_num in self.packet_history:
                    # Retransmit the packet
                    packet_data = self.packet_history[seq_num]
                    self.socket.sendto(packet_data, (self.dest_ip, self.dest_port))
                    print(f"Retransmitted packet {seq_num}")