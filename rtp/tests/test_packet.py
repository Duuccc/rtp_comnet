"""
Tests for RTP packet implementation
"""

import unittest
from ..core.packet import RTPPacket

class TestRTPPacket(unittest.TestCase):
    def setUp(self):
        self.payload = b"test payload"
        self.packet = RTPPacket(
            payload_type=RTPPacket.PT_AUDIO,
            seq_num=12345,
            timestamp=67890,
            ssrc=0x12345678,
            payload=self.payload
        )
    
    def test_packet_creation(self):
        """Test basic packet creation"""
        self.assertEqual(self.packet.payload_type, RTPPacket.PT_AUDIO)
        self.assertEqual(self.packet.seq_num, 12345)
        self.assertEqual(self.packet.timestamp, 67890)
        self.assertEqual(self.packet.ssrc, 0x12345678)
        self.assertEqual(self.packet.payload, self.payload)
    
    def test_packet_encoding_decoding(self):
        """Test packet encoding and decoding"""
        encoded = self.packet.encode()
        decoded = RTPPacket.decode(encoded)
        
        self.assertEqual(decoded.payload_type, self.packet.payload_type)
        self.assertEqual(decoded.seq_num, self.packet.seq_num)
        self.assertEqual(decoded.timestamp, self.packet.timestamp)
        self.assertEqual(decoded.ssrc, self.packet.ssrc)
        self.assertEqual(decoded.payload, self.packet.payload)
    
    def test_nack_packet(self):
        """Test NACK packet creation and parsing"""
        missing_seq_nums = [12345, 12346, 12347]
        nack_packet = RTPPacket.create_nack(missing_seq_nums)
        
        self.assertEqual(nack_packet.payload_type, RTPPacket.PT_NACK)
        self.assertEqual(nack_packet.get_nack_sequence_numbers(), missing_seq_nums)

if __name__ == '__main__':
    unittest.main() 