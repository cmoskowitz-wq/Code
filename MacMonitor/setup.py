"""
Mosko Meter v7.0 - Professional System Monitor Setup
"""

from setuptools import setup, find_packages
import os

# Read the README file
def read_readme():
    with open(os.path.join(os.path.dirname(__file__), 'README.md'), encoding='utf-8') as f:
        return f.read()

# Read requirements
def read_requirements():
    with open(os.path.join(os.path.dirname(__file__), 'requirements.txt'), encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="mosko-meter",
    version="7.0.0",
    author="Chris Moskowitz",
    author_email="cmoskowitz@gmail.com",
    description="Professional real-time system monitoring application for macOS",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/cmoskowitz/mosko-meter",
    packages=find_packages(),
    py_modules=['main'],
    include_package_data=True,
    install_requires=read_requirements(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "License :: Other/Proprietary License",
        "Operating System :: MacOS :: MacOS X",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: System :: Monitoring",
        "Topic :: Utilities",
    ],
    python_requires=">=3.8",
    entry_points={
        'console_scripts': [
            'mosko-meter=main:main',
        ],
    },
    keywords="system monitor macos cpu memory network latency process monitoring",
    project_urls={
        "Bug Reports": "mailto:cmoskowitz@gmail.com",
        "Source": "https://github.com/cmoskowitz/mosko-meter",
        "Documentation": "https://github.com/cmoskowitz/mosko-meter#readme",
    },
)