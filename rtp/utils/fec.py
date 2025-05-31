import struct
from rtp.core.packet import RTPPacket

class FECHandler:
    def __init__(self, group_size=4):
        """Initialize FEC handler
        
        Args:
            group_size: Number of packets in each FEC group
        """
        self.group_size = group_size
        self.packet_buffer = []
        self.fec_packet = None
        
    def add_packet(self, packet):
        """Add a packet to the current FEC group"""
        self.packet_buffer.append(packet)
        
        if len(self.packet_buffer) == self.group_size:
            self._generate_fec_packet()
            return self.fec_packet
        return None
        
    def _generate_fec_packet(self):
        """Generate FEC packet for current group"""
        if len(self.packet_buffer) < self.group_size:
            return None
            
        # Get sequence numbers of packets in group
        seq_nums = [p.seq_num for p in self.packet_buffer]
        
        # Pack sequence numbers into metadata
        metadata = struct.pack('!' + 'H' * len(seq_nums), *seq_nums)
        
        # XOR all payloads together
        fec_payload = self.packet_buffer[0].payload
        for packet in self.packet_buffer[1:]:
            fec_payload = bytes(a ^ b for a, b in zip(fec_payload, packet.payload))
        
        # Create FEC packet
        fec_packet = RTPPacket(
            payload_type=RTPPacket.PT_FEC,
            seq_num=self.packet_buffer[-1].seq_num + 1,
            timestamp=self.packet_buffer[-1].timestamp,
            ssrc=self.packet_buffer[0].ssrc,
            payload=metadata + fec_payload
        )
        
        # Clear current group
        self.packet_buffer = []
        
        return fec_packet
        
    def recover_packet(self, fec_packet, available_packets):
        """Recover a lost packet using FEC data
        
        Args:
            fec_packet: The FEC packet for the group
            available_packets: List of available packets in the group
            
        Returns:
            Recovered RTP packet or None if recovery not possible
        """
        if not fec_packet or fec_packet.payload_type != RTPPacket.PT_FEC:
            return None
            
        # Extract sequence numbers from FEC packet
        num_packets = len(fec_packet.payload) // 2
        seq_nums = struct.unpack('!' + 'H' * num_packets, 
                               fec_packet.payload[:num_packets * 2])
        
        # Find missing sequence number
        available_seq_nums = set(p.seq_num for p in available_packets)
        missing_seq_nums = set(seq_nums) - available_seq_nums
        
        if len(missing_seq_nums) != 1:
            return None  # Can only recover one lost packet
            
        missing_seq_num = missing_seq_nums.pop()
        
        # XOR FEC data with available packets to recover missing packet
        fec_data = bytearray(fec_packet.payload[num_packets * 2:])
        
        for packet in available_packets:
            packet_data = packet.encode()
            for i in range(len(fec_data)):
                if i < len(packet_data):
                    fec_data[i] ^= packet_data[i]
        
        # Create recovered packet
        recovered_packet = RTPPacket.decode(bytes(fec_data))
        recovered_packet.seq_num = missing_seq_num
        
        return recovered_packet 