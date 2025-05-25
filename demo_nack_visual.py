import time
import threading
import random
from rtp.core.packet import RTPPacket
from rtp.core.sender import RTPSender
from rtp.core.receiver import RTPReceiver
from rtp.utils.retransmission import RetransmissionHandler

def print_packet_status(seq_num, status, color='white'):
    """Print packet status with color"""
    colors = {
        'white': '\033[0m',
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m'
    }
    print(f"{colors[color]}[{seq_num:4d}] {status}{colors['white']}")

def simulate_network(sender, receiver, loss_rate=0.2, delay=0.1):
    """Simulate network with packet loss and delay"""
    while True:
        try:
            # Get next packet from sender's buffer
            if not sender.packet_buffer:
                time.sleep(0.1)
                continue
                
            # Get the next packet
            seq_num = min(sender.packet_buffer.keys())
            packet = sender.packet_buffer[seq_num]
            del sender.packet_buffer[seq_num]
            
            # Simulate packet loss
            if random.random() < loss_rate:
                print_packet_status(packet.seq_num, "LOST", 'red')
                continue
                
            # Simulate network delay
            time.sleep(delay)
            
            # Forward packet to receiver
            print_packet_status(packet.seq_num, "RECEIVED", 'green')
            receiver.process_packet(packet)
            
            # Check for NACK
            nack = receiver.request_retransmission()
            if nack:
                missing_seqs = nack.get_nack_sequence_numbers()
                for seq in missing_seqs:
                    print_packet_status(seq, "NACK SENT", 'yellow')
                # Handle NACK and retransmit
                rtx_packets = sender.handle_nack(nack)
                for rtx in rtx_packets:
                    print_packet_status(rtx.seq_num, "RETRANSMITTED", 'blue')
                    time.sleep(delay)
                    receiver.process_packet(rtx)
                    
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error in network simulation: {e}")
            break

def main():
    # Create sender and receiver
    sender = RTPSender("127.0.0.1", 5000)
    receiver = RTPReceiver("127.0.0.1", 5000)
    
    # Create test data
    data_chunks = [f"Chunk {i}".encode() for i in range(20)]
    
    print("\n=== RTP NACK and Retransmission Demo ===")
    print("Legend:")
    print("  [XXXX] RECEIVED    - Packet successfully received")
    print("  [XXXX] LOST        - Packet lost in network")
    print("  [XXXX] NACK SENT   - NACK packet sent for missing packet")
    print("  [XXXX] RETRANSMITTED - Packet retransmitted after NACK")
    print("\nStarting simulation...\n")
    
    # Start network simulation in a separate thread
    network_thread = threading.Thread(
        target=simulate_network,
        args=(sender, receiver, 0.2, 0.1)
    )
    network_thread.daemon = True
    network_thread.start()
    
    # Send packets
    for chunk in data_chunks:
        try:
            packets = sender.send_audio(chunk)
            time.sleep(0.2)  # Delay between chunks
        except Exception as e:
            print(f"Error sending packet: {e}")
            break
    
    # Wait for network simulation to complete
    network_thread.join(timeout=5)
    
    print("\nSimulation completed!")

if __name__ == "__main__":
    main() 