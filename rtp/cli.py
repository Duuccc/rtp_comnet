"""
Command line interface for RTP package
"""

import argparse
import threading
import time
import logging
from pathlib import Path

from .core.sender import RTPSender
from .core.receiver import RTPReceiver
from .utils.network_simulator import SimulatedNetwork
from .config import RTPConfig, default_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_args():
    parser = argparse.ArgumentParser(description='RTP Audio Streaming')
    parser.add_argument('--mode', choices=['sender', 'receiver', 'both'], default='both',
                      help='Operation mode')
    parser.add_argument('--config', type=str, help='Path to configuration file')
    parser.add_argument('--sender-ip', default=default_config.sender_ip)
    parser.add_argument('--sender-port', type=int, default=default_config.sender_port)
    parser.add_argument('--receiver-ip', default=default_config.receiver_ip)
    parser.add_argument('--receiver-port', type=int, default=default_config.receiver_port)
    parser.add_argument('--duration', type=float, default=10.0,
                      help='Duration to run in seconds')
    parser.add_argument('--interval', type=float, default=0.02,
                      help='Interval between packets in seconds')
    parser.add_argument('--audio', help='Path to input.wav to stream')
    parser.add_argument('--simulate-network', action='store_true',
                      help='Enable simulated network middlebox')
    parser.add_argument('--middlebox-port', type=int, default=default_config.middlebox_port)
    parser.add_argument('--receiver-listen-port', type=int, default=default_config.receiver_listen_port)
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                      default='INFO', help='Logging level')
    return parser.parse_args()

def main():
    args = parse_args()
    
    # Set log level
    logging.getLogger().setLevel(args.log_level)
    
    # Load configuration
    config = default_config
    if args.config:
        config = RTPConfig.from_file(args.config)
    
    # Override config with command line arguments
    config.sender_ip = args.sender_ip
    config.sender_port = args.sender_port
    config.receiver_ip = args.receiver_ip
    config.receiver_port = args.receiver_port
    config.simulate_network = args.simulate_network
    config.middlebox_port = args.middlebox_port
    config.receiver_listen_port = args.receiver_listen_port
    
    sender = None
    receiver = None
    network_sim = None

    try:
        # Start network simulator if enabled
        if config.simulate_network:
            network_sim = SimulatedNetwork(
                listen_port=config.middlebox_port,
                forward_ip=config.receiver_ip,
                forward_port=config.receiver_listen_port,
                drop_rate=config.drop_rate,
                max_delay=config.max_delay,
                reorder_rate=config.reorder_rate,
                duplicate_rate=config.duplicate_rate
            )
            threading.Thread(target=network_sim.start, daemon=True).start()
            logger.info("Network simulator started")

        # Start sender if needed
        if args.mode in ['sender', 'both']:
            sender = RTPSender(config.receiver_ip, config.sender_port)
            if args.audio:
                sender.set_audio_file(args.audio)
            logger.info("Sender initialized")

        # Start receiver if needed
        if args.mode in ['receiver', 'both']:
            listen_port = config.receiver_listen_port if config.simulate_network else config.receiver_port
            receiver = RTPReceiver(config.receiver_ip, listen_port)
            receiver.start_receiving()
            logger.info("Receiver started")
            time.sleep(0.5)  # Give receiver time to start

        # Start sending if sender is active
        if sender:
            sender.start_sending(interval=args.interval, duration=args.duration)
            while sender.running:
                time.sleep(0.1)
        elif receiver:
            time.sleep(args.duration)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error occurred: {e}", exc_info=True)
    finally:
        # Cleanup
        if sender:
            sender.stop_sending()
        if receiver:
            receiver.stop_receiving()
        if network_sim:
            network_sim.stop()
        logger.info("Cleanup completed")

if __name__ == '__main__':
    main() 