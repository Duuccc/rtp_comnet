from setuptools import setup, find_packages

setup(
    name="rtp-audio",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "numpy>=1.21.0",
        "soundfile>=0.10.3",
    ],
    author="Your Name",
    author_email="your.email@example.com",
    description="A Python implementation of RTP (Real-time Transport Protocol) for audio streaming",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/rtp-audio",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "rtp-sender=rtp.cli:main",
        ],
    },
) 