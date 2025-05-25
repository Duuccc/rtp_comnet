import socket
import threading
import time
import wave
from rtp.core.packet import RTPPacket
from collections import defaultdict
from rtp.utils.fec import FECHandler
from rtp.utils.retransmission import RetransmissionHandler

class RTPReceiver:
    def __init__(self, bind_ip, bind_port, expected_ssrc=None, buffer_size=1000, group_size=4):
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
            'out_of_order': 0,
            'nacks_sent': 0,
            'retransmissions_received': 0
        }
        self.sender_addr = None
        self.missing_packets = set()  # Track missing sequence numbers
        self.received_packets = {}  # Buffer for out-of-order packets
        self.last_nack_time = {}  # Track when NACK was last sent for each sequence number
        self.nack_timeout = 0.1  # Wait 100ms before resending NACK
        self.max_packet_buffer = 1000  # Maximum number of packets to buffer
        
        self.expected_ssrc = expected_ssrc
        self.fec_packets = {}  # group_start_seq -> fec_packet
        self.next_seq = 0  # Next expected sequence number
        self.buffer_size = buffer_size
        
        self.fec_handler = FECHandler(group_size=group_size)
        self.rtx_handler = RetransmissionHandler(buffer_size=buffer_size)
        
        self.lock = threading.Lock()
    
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
    
    def _send_nack(self, missing_seq_nums):
        """Send NACK packet for missing sequence numbers"""
        if not self.sender_addr:
            return
        
        current_time = time.time()
        # Filter sequence numbers that haven't been NACKed recently
        seq_nums_to_nack = []
        for seq_num in missing_seq_nums:
            if (seq_num not in self.last_nack_time or 
                current_time - self.last_nack_time[seq_num] > self.nack_timeout):
                seq_nums_to_nack.append(seq_num)
                self.last_nack_time[seq_num] = current_time
        
        if seq_nums_to_nack:
            nack_packet = RTPPacket.create_nack(seq_nums_to_nack, self.stats.get('ssrc', 0))
            self.socket.sendto(nack_packet.encode(), self.sender_addr)
            self.stats['nacks_sent'] += 1
            print(f"Sent NACK for sequences: {seq_nums_to_nack}")

    def _process_packet(self, packet, addr):
        """Xử lý gói tin RTP nhận được"""
        # Store sender address for NACK packets
        if not self.sender_addr:
            self.sender_addr = addr
            self.stats['ssrc'] = packet.ssrc

        # Handle NACK packets separately
        if packet.payload_type == RTPPacket.PT_NACK:
            return

        self.stats['packets_received'] += 1
        
        # Kiểm tra thứ tự gói tin
        if self.stats['last_seq'] is not None:
            expected_seq = (self.stats['last_seq'] + 1) % 65536
            
            # If packet is in sequence
            if packet.seq_num == expected_seq:
                self._write_packet(packet)
                # Process any buffered packets that are now in sequence
                self._process_buffered_packets()
            
            # If packet is out of order
            else:
                if ((packet.seq_num < expected_seq and not (expected_seq > 60000 and packet.seq_num < 5000)) or
                    (expected_seq < 5000 and packet.seq_num > 60000)):
                    # Late packet - check if it was missing
                    if packet.seq_num in self.missing_packets:
                        self.missing_packets.remove(packet.seq_num)
                        self.stats['retransmissions_received'] += 1
                    else:
                        self.stats['out_of_order'] += 1
                    # Buffer the packet
                    self.received_packets[packet.seq_num] = packet
                else:
                    # Gap in sequence numbers - mark packets as missing
                    if packet.seq_num > expected_seq:
                        missing_range = range(expected_seq, packet.seq_num)
                    else:  # Sequence number wrapped around
                        missing_range = list(range(expected_seq, 65536)) + list(range(0, packet.seq_num))
                    
                    for seq in missing_range:
                        if seq not in self.received_packets:  # Don't mark buffered packets as missing
                            self.missing_packets.add(seq)
                    
                    self.stats['lost_packets'] += len(missing_range)
                    # Send NACK for missing packets
                    self._send_nack(missing_range)
                    # Buffer the current packet
                    self.received_packets[packet.seq_num] = packet
        else:
            # First packet
            self._write_packet(packet)
        
        self.stats['last_seq'] = packet.seq_num
        
        # Clean up old buffered packets
        if len(self.received_packets) > self.max_packet_buffer:
            oldest_seq = min(self.received_packets.keys())
            del self.received_packets[oldest_seq]
            if oldest_seq in self.missing_packets:
                self.missing_packets.remove(oldest_seq)
        
        # Print stats
        loss_rate = self.stats['lost_packets'] / (self.stats['packets_received'] + self.stats['lost_packets']) * 100 if (self.stats['packets_received'] + self.stats['lost_packets']) > 0 else 0
        print(f"Stats: Received={self.stats['packets_received']}, Lost={self.stats['lost_packets']}, "
              f"Out-of-order={self.stats['out_of_order']}, Loss Rate={loss_rate:.2f}%, "
              f"NACKs Sent={self.stats['nacks_sent']}, "
              f"Retransmissions={self.stats['retransmissions_received']}")

    def _write_packet(self, packet):
        """Write packet payload to audio file and update state"""
        if self.audio_writer:
            self.audio_writer.writeframes(packet.payload)
        print(f"Processed packet: {packet}")

    def _process_buffered_packets(self):
        """Process any buffered packets that are now in sequence"""
        while True:
            next_seq = (self.stats['last_seq'] + 1) % 65536
            if next_seq in self.received_packets:
                packet = self.received_packets.pop(next_seq)
                self._write_packet(packet)
                self.stats['last_seq'] = next_seq
                if next_seq in self.missing_packets:
                    self.missing_packets.remove(next_seq)
            else:
                break

    def process_packet(self, packet):
        """Process received packet and attempt recovery if needed"""
        with self.lock:
            if packet.payload_type == RTPPacket.PT_FEC:
                # Store FEC packet
                group_start = self._get_group_start(packet.seq_num)
                self.fec_packets[group_start] = packet
                return self._try_fec_recovery(group_start)
                
            elif packet.payload_type == RTPPacket.PT_RTX:
                # Handle retransmitted packet
                original_payload = self.rtx_handler.process_rtx_packet(packet)
                if original_payload:
                    seq_num = packet.get_original_seq_num()
                    if seq_num in self.missing_packets:
                        self.missing_packets.remove(seq_num)
                        self.received_packets[seq_num] = original_payload
                        return [original_payload]
                return []
                
            else:
                # Regular packet
                self.received_packets[packet.seq_num] = packet
                self._update_missing_packets(packet.seq_num)
                return [packet]
    
    def _get_group_start(self, seq_num):
        """Get the starting sequence number for the FEC group"""
        return (seq_num // self.fec_handler.group_size) * self.fec_handler.group_size
    
    def _update_missing_packets(self, seq_num):
        """Update the set of missing packets"""
        if seq_num > self.next_seq:
            # Add all missing sequence numbers
            self.missing_packets.update(range(self.next_seq, seq_num))
        self.next_seq = max(self.next_seq, seq_num + 1)
    
    def _try_fec_recovery(self, group_start):
        """Try to recover missing packets using FEC"""
        fec_packet = self.fec_packets.get(group_start)
        if not fec_packet:
            return []
            
        # Get available packets in the group
        group_end = group_start + self.fec_handler.group_size
        available_packets = []
        for seq in range(group_start, group_end):
            if seq in self.received_packets:
                available_packets.append(self.received_packets[seq])
        
        # Try recovery
        recovered_packet = self.fec_handler.recover_packet(fec_packet, available_packets)
        if recovered_packet:
            self.received_packets[recovered_packet.seq_num] = recovered_packet
            self.missing_packets.remove(recovered_packet.seq_num)
            return [recovered_packet]
        
        return []
    
    def request_retransmission(self):
        """Create NACK packet for missing packets"""
        with self.lock:
            if not self.missing_packets:
                return None
                
            # Create NACK packet
            nack_packet = RTPPacket.create_nack(
                list(self.missing_packets),
                self.expected_ssrc or 0
            )
            return nack_packet
    
    def get_ordered_packets(self):
        """Get received packets in order"""
        with self.lock:
            ordered = []
            current_seq = min(self.received_packets.keys())
            while current_seq in self.received_packets:
                ordered.append(self.received_packets[current_seq])
                current_seq += 1
            return ordered