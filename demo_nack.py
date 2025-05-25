import time
import threading
from rtp.core.packet import RTPPacket
from rtp.core.sender import RTPSender
from rtp.core.receiver import RTPReceiver
from rtp.utils.retransmission import RetransmissionHandler

def simulate_packet_loss(packets, loss_rate=0.2):
    """Simulate packet loss in network"""
    import random
    return [p for p in packets if random.random() > loss_rate]

def run_sender(sender, data_chunks):
    """Run sender thread"""
    all_packets = []
    for chunk in data_chunks:
        # Send data
        packets = sender.send_audio(chunk)
        all_packets.extend(packets)
        time.sleep(0.01)  # Simulate sending delay
    return all_packets

def run_receiver(receiver, received_packets):
    """Run receiver thread"""
    recovered_data = []
    missing_reported = set()
    
    for packet in received_packets:
        # Process received packet
        processed = receiver.process_packet(packet)
        recovered_data.extend(processed)
        
        # Check for missing packets and request retransmission
        nack = receiver.request_retransmission()
        if nack:
            missing_seqs = set(nack.get_nack_sequence_numbers())
            new_missing = missing_seqs - missing_reported
            if new_missing:
                print(f"Requesting retransmission for packets: {new_missing}")
                missing_reported.update(new_missing)
    
    return recovered_data

def main():
    # Create test data
    data_chunks = [f"Chunk {i}".encode() for i in range(100)]
    
    # Create sender and receiver
    sender = RTPSender("127.0.0.1", 5000)
    receiver = RTPReceiver("127.0.0.1", 5000)
    
    # Run sender
    print("Starting sender...")
    sent_packets = run_sender(sender, data_chunks)
    print(f"Sent {len(sent_packets)} packets")
    
    # Simulate network loss
    print("\nSimulating network loss...")
    received_packets = simulate_packet_loss(sent_packets)
    print(f"Lost {len(sent_packets) - len(received_packets)} packets")
    
    # Run receiver
    print("\nStarting receiver...")
    recovered_data = run_receiver(receiver, received_packets)
    
    # Print statistics
    print("\nStatistics:")
    print(f"Original packets: {len(sent_packets)}")
    print(f"Received packets: {len(received_packets)}")
    print(f"Recovered packets: {len(recovered_data)}")
    
    # Check recovery success
    recovery_rate = len(recovered_data) / len(sent_packets)
    print(f"Recovery rate: {recovery_rate:.2%}")

if __name__ == "__main__":
    main() 