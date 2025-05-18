import struct

class RTPPacket:
    HEADER_SIZE = 12  # Kích thước phần header cố định (byte)
    
    def __init__(self, payload_type=96, seq_num=0, timestamp=0, ssrc=0, payload=b''):
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