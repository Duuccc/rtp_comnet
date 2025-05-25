import struct

# RTP Header Format:
#  0                   1                   2                   3
#  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
# |V=2|P|X|  CC   |M|     PT      |       sequence number         |
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
# |                           timestamp                           |
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
# |           synchronization source (SSRC)  identifier            |
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
# |            contributing source (CSRC) identifiers             |
# |                             ....                              |
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

class RTPPacket:
    HEADER_SIZE = 12  # Kích thước phần header cố định (byte)
    
    # Add packet types
    PT_AUDIO = 96  # Audio payload type
    PT_NACK = 65  # NACK control packet type
    PT_FEC = 97   # FEC packet type
    PT_RTX = 98   # Retransmission packet type
    
    def __init__(self, payload_type=PT_AUDIO, seq_num=0, timestamp=0, ssrc=0, payload=b''):
        self.version = 2         # Phiên bản RTP (2 bits)
        self.padding = 0         # Padding flag (1 bit)
        self.extension = 0       # Extension flag (1 bit)
        self.cc = 0              # CSRC count (4 bits)
        self.marker = 0          # Marker bit (1 bit)
        self.payload_type = payload_type  # Loại payload (7 bits)
        self.seq_num = seq_num   # Số thứ tự gói tin (16 bits)
        self.timestamp = timestamp  # Timestamp (32 bits)
        self.ssrc = ssrc         # SSRC identifier (32 bits)
        self.csrc = []           # CSRC list
        self.payload = payload   # Payload data
        self.original_seq = None # Original sequence number for retransmitted packets
    
    def encode(self):
        """Đóng gói dữ liệu thành gói tin RTP"""
        # Byte đầu tiên: V=2|P|X|CC (version, padding, extension, CSRC count)
        first_byte = (self.version << 6) | (self.padding << 5) | (self.extension << 4) | self.cc
        
        # Byte thứ hai: M|PT (marker bit và payload type)
        second_byte = (self.marker << 7) | self.payload_type
        
        # Đóng gói header
        header = struct.pack('!BBH', first_byte, second_byte, self.seq_num)
        header += struct.pack('!II', self.timestamp, self.ssrc)
        
        # Thêm CSRC identifiers (nếu có)
        for csrc in self.csrc:
            header += struct.pack('!I', csrc)
        
        # Kết hợp header và payload
        return header + self.payload
    
    @classmethod
    def decode(cls, packet_bytes):
        """Giải mã gói tin RTP"""
        if len(packet_bytes) < cls.HEADER_SIZE:
            raise ValueError("Packet too small to be a valid RTP packet")
            
        # Parse header
        first_byte, second_byte, seq_num = struct.unpack('!BBH', packet_bytes[0:4])
        timestamp, ssrc = struct.unpack('!II', packet_bytes[4:12])
        
        # Extract fields from first byte
        version = (first_byte >> 6) & 0x03
        padding = (first_byte >> 5) & 0x01
        extension = (first_byte >> 4) & 0x01
        cc = first_byte & 0x0F
        
        # Extract fields from second byte
        marker = (second_byte >> 7) & 0x01
        payload_type = second_byte & 0x7F
        
        # Extract CSRC list
        csrc_list = []
        for i in range(cc):
            if 12 + i*4 < len(packet_bytes):
                csrc, = struct.unpack('!I', packet_bytes[12+i*4:16+i*4])
                csrc_list.append(csrc)
        
        # Extract payload
        header_size = cls.HEADER_SIZE + (cc * 4)
        payload = packet_bytes[header_size:]
        
        # Create RTP packet object
        packet = cls(payload_type, seq_num, timestamp, ssrc, payload)
        packet.version = version
        packet.padding = padding
        packet.extension = extension
        packet.cc = cc
        packet.marker = marker
        packet.csrc = csrc_list
        
        return packet
    
    def __str__(self):
        """Hiển thị thông tin gói tin"""
        return (f"RTP Packet [V={self.version}, P={self.padding}, X={self.extension}, "
                f"CC={self.cc}, M={self.marker}, PT={self.payload_type}, "
                f"Seq={self.seq_num}, Time={self.timestamp}, SSRC=0x{self.ssrc:08x}, "
                f"Payload Size={len(self.payload)}]")

    @classmethod
    def create_nack(cls, missing_seq_nums, ssrc):
        """Create a NACK packet for requesting retransmission of missing packets
        
        Args:
            missing_seq_nums: List of sequence numbers of missing packets
            ssrc: SSRC identifier of the stream
        """
        # Pack missing sequence numbers into payload
        payload = b''
        for seq_num in missing_seq_nums:
            payload += struct.pack('!H', seq_num)
        
        return cls(
            payload_type=cls.PT_NACK,
            seq_num=0,  # NACK packets don't need sequence numbers
            timestamp=0,  # NACK packets don't need timestamps
            ssrc=ssrc,
            payload=payload
        )

    def get_nack_sequence_numbers(self):
        """Extract missing sequence numbers from NACK packet payload"""
        if self.payload_type != self.PT_NACK:
            raise ValueError("Not a NACK packet")
        
        missing_seq_nums = []
        for i in range(0, len(self.payload), 2):
            seq_num, = struct.unpack('!H', self.payload[i:i+2])
            missing_seq_nums.append(seq_num)
        return missing_seq_nums

    @classmethod
    def create_rtx_packet(cls, original_packet):
        """Create a retransmission packet
        
        Args:
            original_packet: The original RTP packet to retransmit
        """
        # Store original sequence number in payload
        rtx_payload = struct.pack('!H', original_packet.seq_num) + original_packet.payload
        
        rtx_packet = cls(
            payload_type=cls.PT_RTX,
            seq_num=original_packet.seq_num,  # Use same sequence number
            timestamp=original_packet.timestamp,
            ssrc=original_packet.ssrc,
            payload=rtx_payload
        )
        rtx_packet.original_seq = original_packet.seq_num
        return rtx_packet

    def is_rtx_packet(self):
        """Check if this is a retransmission packet"""
        return self.payload_type == self.PT_RTX

    def get_original_seq_num(self):
        """Get original sequence number from retransmission packet"""
        if not self.is_rtx_packet():
            return None
        return struct.unpack('!H', self.payload[:2])[0]

    def get_rtx_payload(self):
        """Get original payload from retransmission packet"""
        if not self.is_rtx_packet():
            return None
        return self.payload[2:]