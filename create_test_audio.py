import numpy as np
import soundfile as sf

def create_test_wav(filename, duration=3.0, frequency=440.0, sample_rate=8000):
    """
    Create a test WAV file with a sine wave
    
    Args:
        filename: Output WAV file name
        duration: Duration in seconds
        frequency: Frequency of the sine wave in Hz
        sample_rate: Sample rate in Hz
    """
    # Generate time array
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    # Generate sine wave
    audio = np.sin(2 * np.pi * frequency * t)
    
    # Normalize to 16-bit integer range
    audio = np.int16(audio * 32767)
    
    # Save as WAV file
    sf.write(filename, audio, sample_rate)
    print(f"Created test WAV file: {filename}")
    print(f"Duration: {duration} seconds")
    print(f"Frequency: {frequency} Hz")
    print(f"Sample rate: {sample_rate} Hz")

if __name__ == "__main__":
    # Create a test WAV file with a 440 Hz sine wave (A4 note)
    create_test_wav("test_audio.wav") 