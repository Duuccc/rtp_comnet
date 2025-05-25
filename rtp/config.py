"""
Configuration management for RTP package
"""

import os
import json
from dataclasses import dataclass
from typing import Optional

@dataclass
class RTPConfig:
    """RTP configuration settings"""
    # Network settings
    sender_ip: str = "127.0.0.1"
    sender_port: int = 5000
    receiver_ip: str = "127.0.0.1"
    receiver_port: int = 5000
    
    # Audio settings
    sample_rate: int = 8000
    channels: int = 1
    sample_width: int = 2
    
    # RTP settings
    payload_type: int = 0  # Dynamic payload type
    timestamp_increment: int = 160  # 20ms @ 8kHz
    
    # FEC settings
    fec_group_size: int = 4
    
    # Retransmission settings
    history_size: int = 1000
    
    # Network simulation settings
    simulate_network: bool = False
    middlebox_port: int = 5000
    receiver_listen_port: int = 6000
    drop_rate: float = 0.1
    max_delay: float = 0.05
    reorder_rate: float = 0.2
    duplicate_rate: float = 0.05

    @classmethod
    def from_file(cls, config_path: str) -> 'RTPConfig':
        """Load configuration from a JSON file"""
        if not os.path.exists(config_path):
            return cls()
            
        with open(config_path, 'r') as f:
            config_dict = json.load(f)
        return cls(**config_dict)
    
    def save(self, config_path: str):
        """Save configuration to a JSON file"""
        config_dict = {
            field: getattr(self, field)
            for field in self.__dataclass_fields__
        }
        with open(config_path, 'w') as f:
            json.dump(config_dict, f, indent=4)

# Default configuration
default_config = RTPConfig() 