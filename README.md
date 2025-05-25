# RTP Audio Streaming

A Python implementation of RTP (Real-time Transport Protocol) for audio streaming with features like:
- Audio streaming over UDP
- Forward Error Correction (FEC)
- Packet retransmission
- Network simulation for testing
- Configurable audio parameters

## Installation

```bash
pip install -e .
```

## Usage

### Basic Usage

1. Start the receiver:
```bash
python -m rtp.cli --mode receiver --receiver-port 5000
```

2. Start the sender:
```bash
python -m rtp.cli --mode sender --receiver-ip 127.0.0.1 --receiver-port 5000 --audio input.wav
```

### Network Simulation

To test with simulated network conditions:

```bash
python -m rtp.cli --mode both --simulate-network --middlebox-port 5000 --receiver-listen-port 6000
```

## Features

- **RTP Implementation**: Full RTP packet handling with sequence numbers and timestamps
- **FEC Support**: Forward Error Correction for packet loss recovery
- **Retransmission**: NACK-based packet retransmission
- **Network Simulation**: Simulate network conditions like packet loss, delay, and reordering
- **Audio Support**: Stream audio files in WAV format

## Project Structure

```
rtp/
├── __init__.py
├── cli.py              # Command line interface
├── config.py           # Configuration management
├── core/
│   ├── __init__.py
│   ├── packet.py      # RTP packet implementation
│   ├── sender.py      # RTP sender implementation
│   └── receiver.py    # RTP receiver implementation
├── utils/
│   ├── __init__.py
│   ├── fec.py         # Forward Error Correction
│   └── retransmission.py  # Packet retransmission
└── tests/             # Test suite
```

## Configuration

The project can be configured through command line arguments or a configuration file. See `rtp/config.py` for available options.

## Development

1. Clone the repository
2. Install development dependencies:
```bash
pip install -e ".[dev]"
```
3. Run tests:
```bash
pytest
```

## License

MIT License 