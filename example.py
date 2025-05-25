from rtp.packet import RTPPacket
from rtp.fec import FECHandler
from rtp.retransmission import RetransmissionHandler

def simulate_packet_loss():
    # Create handlers
    fec_handler = FECHandler(group_size=4)
    rtx_handler = RetransmissionHandler()
    
    # Create some test packets
    packets = []
    for i in range(10):
        packet = RTPPacket(
            payload_type=RTPPacket.PT_AUDIO,
            seq_num=i,
            timestamp=i * 1000,
            ssrc=12345,
            payload=f"Test packet {i}".encode()
        )
        packets.append(packet)
    
    # Sender side: Generate FEC packets and buffer for retransmission
    fec_packets = []
    for packet in packets:
        # Add to retransmission buffer
        rtx_handler.add_packet(packet)
        
        # Generate FEC packet when group is complete
        fec_packet = fec_handler.add_packet(packet)
        if fec_packet:
            fec_packets.append(fec_packet)
    
    # Simulate packet loss (remove packet 2)
    received_packets = packets.copy()
    lost_packet = received_packets.pop(2)
    print(f"Lost packet with sequence number {lost_packet.seq_num}")
    
    # Receiver side: Try to recover using FEC
    available_packets = received_packets[0:3]  # First FEC group
    recovered_packet = fec_handler.recover_packet(fec_packets[0], available_packets)
    
    if recovered_packet:
        print(f"Recovered packet using FEC: {recovered_packet}")
    else:
        # If FEC fails, use retransmission
        print("FEC recovery failed, using retransmission")
        # Create NACK packet
        nack_packet = RTPPacket.create_nack([lost_packet.seq_num], ssrc=12345)
        
        # Handle NACK on sender side
        rtx_packets = rtx_handler.handle_nack(nack_packet)
        
        # Process retransmitted packet on receiver side
        for rtx_packet in rtx_packets:
            original_payload = rtx_handler.process_rtx_packet(rtx_packet)
            print(f"Recovered packet using retransmission: {original_payload}")

if __name__ == "__main__":
    simulate_packet_loss() 