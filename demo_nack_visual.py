import time
import threading
import random
from queue import Queue
from rtp.core.sender import RTPSender
from rtp.core.receiver import RTPReceiver
from rtp.core.packet import RTPPacket

def print_packet_status(seq_num, status):
    """Print packet status with color coding"""
    colors = {
        'RECEIVED': '\033[92m',  # Green
        'LOST': '\033[91m',      # Red
        'NACK': '\033[93m',      # Yellow
        'RETRANSMITTED': '\033[94m'  # Blue
    }
    reset = '\033[0m'
    print(f"{colors[status]}[{seq_num:04d}] {status}{reset}")

def sender_thread_func(sender, packet_queue, num_packets, interval):
    for i in range(num_packets):
        payload = f"Test packet {i}".encode()
        packet = sender.create_packet(payload)
        # Store for retransmission
        sender.rtx_handler.add_packet(packet)
        packet_queue.put(packet)
        time.sleep(interval)

def network_simulation(packet_queue, sender, receiver, loss_rate, delay, nack_queue, num_packets):
    delivered = set()
    while len(delivered) < num_packets:
        if not packet_queue.empty():
            packet = packet_queue.get()
            if random.random() < loss_rate:
                print_packet_status(packet.seq_num, 'LOST')
                # Simulate loss, receiver will NACK
            else:
                print_packet_status(packet.seq_num, 'RECEIVED')
                receiver.process_packet(packet)
                delivered.add(packet.seq_num)
            time.sleep(delay)
        # Handle NACKs
        while not nack_queue.empty():
            nack = nack_queue.get()
            for seq in nack.get_nack_sequence_numbers():
                print_packet_status(seq, 'NACK')
            # Use sender's rtx_handler to get retransmission packets
            rtx_packets = sender.rtx_handler.handle_nack(nack)
            for rtx in rtx_packets:
                print_packet_status(rtx.seq_num, 'RETRANSMITTED')
                receiver.process_packet(rtx)
                delivered.add(rtx.seq_num)
            time.sleep(delay)

def receiver_nack_thread(receiver, nack_queue):
    while True:
        nack = receiver.request_retransmission()
        if nack:
            nack_queue.put(nack)
        time.sleep(0.05)

def main():
    print("=== RTP NACK and Retransmission Demo ===")
    print("Legend:")
    print("  [XXXX] RECEIVED    - Packet successfully received")
    print("  [XXXX] LOST        - Packet lost in network")
    print("  [XXXX] NACK        - NACK packet sent for missing packet")
    print("  [XXXX] RETRANSMITTED - Packet retransmitted after NACK\n")

    num_packets = 30
    loss_rate = 0.2
    delay = 0.05
    interval = 0.05

    sender = RTPSender("127.0.0.1", 5000)
    receiver = RTPReceiver("127.0.0.1", 5000)
    packet_queue = Queue()
    nack_queue = Queue()

    # Start sender thread
    t_sender = threading.Thread(target=sender_thread_func, args=(sender, packet_queue, num_packets, interval))
    t_sender.start()

    # Start receiver NACK thread
    t_nack = threading.Thread(target=receiver_nack_thread, args=(receiver, nack_queue), daemon=True)
    t_nack.start()

    # Start network simulation
    network_simulation(packet_queue, sender, receiver, loss_rate, delay, nack_queue, num_packets)

    t_sender.join()
    print("\nSimulation completed!")

if __name__ == "__main__":
    main() 