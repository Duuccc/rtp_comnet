# main.py
from rtp.sender import RTPSender
from rtp.receiver import RTPReceiver
from rtp.network_simulator import SimulatedNetwork
import argparse
import threading
import time

def main():
    parser = argparse.ArgumentParser(description='RTP Audio Simulation')
    parser.add_argument('--mode', choices=['sender', 'receiver', 'both'], default='both')
    parser.add_argument('--sender-ip', default='127.0.0.1')
    parser.add_argument('--sender-port', type=int, default=5000)
    parser.add_argument('--receiver-ip', default='127.0.0.1')
    parser.add_argument('--receiver-port', type=int, default=5000)
    parser.add_argument('--duration', type=float, default=10.0)
    parser.add_argument('--interval', type=float, default=0.02)
    parser.add_argument('--audio', help='Path to input.wav to stream')
    parser.add_argument('--simulate-network', action='store_true', help='Enable simulated network middlebox')
    parser.add_argument('--middlebox-port', type=int, default=5000, help='Port middlebox listens on')
    parser.add_argument('--receiver-listen-port', type=int, default=6000, help='Receiver port after middlebox')
    args = parser.parse_args()

    sender = None
    receiver = None
    network_sim = None

    try:
        # Nếu mô phỏng lỗi mạng, khởi động middlebox
        if args.simulate_network:
            network_sim = SimulatedNetwork(
                listen_port=args.middlebox_port,
                forward_ip=args.receiver_ip,
                forward_port=args.receiver_listen_port,
                drop_rate=0.1,
                max_delay=0.05,
                reorder_rate=0.2,
                duplicate_rate=0.05
            )
            threading.Thread(target=network_sim.start, daemon=True).start()
            print("[Main] Simulated network enabled")

        if args.mode in ['sender', 'both']:
            sender = RTPSender(args.receiver_ip, args.sender_port)
            if args.audio:
                sender.set_audio_file(args.audio)
        if args.mode in ['receiver', 'both']:
            listen_port = args.receiver_listen_port if args.simulate_network else args.receiver_port
            receiver = RTPReceiver(args.receiver_ip, listen_port)
            receiver.start_receiving()
            time.sleep(0.5)
        if sender:
            sender.start_sending(interval=args.interval, duration=args.duration)
        if sender:
            while sender.running:
                time.sleep(0.1)
        elif receiver:
            time.sleep(args.duration)
    except KeyboardInterrupt:
        print("Interrupted")
    finally:
        if sender:
            sender.stop_sending()
        if receiver:
            receiver.stop_receiving()
        if network_sim:
            network_sim.stop()
        print("Simulation ended")

if __name__ == '__main__':
    main()
