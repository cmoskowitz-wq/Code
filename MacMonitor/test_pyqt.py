#!/usr/bin/env python3
"""
Simple test script to isolate PyQt6 issues
"""

import sys
import os

print("Testing PyQt6 imports...")

try:
    from PyQt6.QtWidgets import QApplication, QLabel
    print("✓ PyQt6.QtWidgets imported successfully")
except ImportError as e:
    print(f"✗ PyQt6.QtWidgets import failed: {e}")
    sys.exit(1)

try:
    from PyQt6.QtCore import Qt
    print("✓ PyQt6.QtCore imported successfully")
except ImportError as e:
    print(f"✗ PyQt6.QtCore import failed: {e}")
    sys.exit(1)

try:
    import pyqtgraph as pg
    print("✓ pyqtgraph imported successfully")
except ImportError as e:
    print(f"✗ pyqtgraph import failed: {e}")
    sys.exit(1)

try:
    import psutil
    print("✓ psutil imported successfully")
except ImportError as e:
    print(f"✗ psutil import failed: {e}")
    sys.exit(1)

print("\nTesting QApplication creation...")
try:
    app = QApplication(sys.argv)
    print("✓ QApplication created successfully")

    # Test basic widget creation
    label = QLabel("Test")
    print("✓ QLabel created successfully")

    print("✓ All basic PyQt6 tests passed!")
    app.quit()

except Exception as e:
    print(f"✗ QApplication test failed: {e}")
    sys.exit(1)

print("🎉 All tests passed! PyQt6 environment is working.")