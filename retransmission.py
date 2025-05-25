from collections import deque
from .packet import RTPPacket

class RetransmissionHandler:
    def __init__(self, buffer_size=1000):
        """Initialize retransmission handler
        
        Args:
            buffer_size: Size of packet buffer for retransmission
        """
        self.packet_buffer = {}  # seq_num -> packet mapping
        self.buffer_size = buffer_size
        self.seq_window = deque(maxlen=buffer_size)  # For maintaining buffer size
        
    def add_packet(self, packet):
        """Add a packet to the retransmission buffer"""
        if packet.is_rtx_packet():
            return
            
        self.packet_buffer[packet.seq_num] = packet
        self.seq_window.append(packet.seq_num)
        
        # Remove old packets if buffer is full
        while len(self.packet_buffer) > self.buffer_size:
            old_seq = self.seq_window.popleft()
            if old_seq in self.packet_buffer:
                del self.packet_buffer[old_seq]
    
    def get_missing_packets(self, start_seq, end_seq):
        """Get list of missing sequence numbers in a range"""
        missing = []
        for seq in range(start_seq, end_seq + 1):
            if seq not in self.packet_buffer:
                missing.append(seq)
        return missing
    
    def handle_nack(self, nack_packet):
        """Handle NACK packet and return list of retransmission packets
        
        Args:
            nack_packet: NACK packet containing sequence numbers to retransmit
            
        Returns:
            List of retransmission packets
        """
        if nack_packet.payload_type != RTPPacket.PT_NACK:
            return []
            
        rtx_packets = []
        for seq_num in nack_packet.get_nack_sequence_numbers():
            if seq_num in self.packet_buffer:
                original_packet = self.packet_buffer[seq_num]
                rtx_packet = RTPPacket.create_rtx_packet(original_packet)
                rtx_packets.append(rtx_packet)
                
        return rtx_packets
    
    def process_rtx_packet(self, rtx_packet):
        """Process retransmission packet and return original packet data
        
        Args:
            rtx_packet: Retransmission packet to process
            
        Returns:
            Original packet payload or None if invalid
        """
        if not rtx_packet.is_rtx_packet():
            return None
            
        return rtx_packet.get_rtx_payload() 