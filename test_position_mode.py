#!/usr/bin/env python3
"""Test position mode switching functionality"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exchanges.bitunix import BitUnixExchange
import time

def test_position_mode():
    """Test position mode functionality"""
    
    exchange = BitUnixExchange()
    
    print("=== Testing Position Mode Functionality ===")
    
    # Test 1: Fetch current position mode
    print("\n1. Fetching current position mode...")
    result = {"completed": False, "mode": None, "error": None}
    
    def mode_callback(status_data):
        status, data = status_data
        result["completed"] = True
        if status == "success":
            result["mode"] = data.get("positionMode")
            result["source"] = data.get("source", "unknown")
            print(f"✅ Current position mode: {result['mode']} (source: {result['source']})")
        else:
            result["error"] = str(data)
            print(f"❌ Error fetching position mode: {result['error']}")
    
    exchange.fetchPositionMode(mode_callback)
    
    # Wait for completion
    timeout = 5
    start_time = time.time()
    while not result["completed"] and (time.time() - start_time) < timeout:
        time.sleep(0.01)
    
    if not result["mode"]:
        print("Could not determine current position mode")
        return
    
    current_mode = result["mode"]
    
    # Test 2: Try to switch position mode
    print(f"\n2. Current mode is {current_mode}")
    new_mode = "ONE_WAY" if current_mode == "HEDGE" else "HEDGE"
    print(f"   Attempting to switch to {new_mode} mode...")
    
    result = {"completed": False, "success": False, "error": None}
    
    def set_mode_callback(status_data):
        status, data = status_data
        result["completed"] = True
        result["success"] = status == "success"
        if status == "success":
            print(f"✅ Successfully switched to {new_mode} mode")
        else:
            result["error"] = str(data)
            print(f"❌ Failed to switch mode: {result['error']}")
    
    exchange.setPositionMode(new_mode, set_mode_callback)
    
    # Wait for completion
    start_time = time.time()
    while not result["completed"] and (time.time() - start_time) < timeout:
        time.sleep(0.01)
    
    # Test 3: Verify the switch
    if result["success"]:
        print("\n3. Verifying position mode switch...")
        time.sleep(1)  # Give it a moment
        
        result = {"completed": False, "mode": None}
        
        def verify_callback(status_data):
            status, data = status_data
            result["completed"] = True
            if status == "success":
                result["mode"] = data.get("positionMode")
                print(f"✅ Verified mode is now: {result['mode']}")
            else:
                print(f"❌ Could not verify mode: {data}")
        
        exchange.fetchPositionMode(verify_callback)
        
        # Wait for completion
        start_time = time.time()
        while not result["completed"] and (time.time() - start_time) < timeout:
            time.sleep(0.01)
        
        # Test 4: Switch back to original mode
        if result["mode"] == new_mode:
            print(f"\n4. Switching back to original mode ({current_mode})...")
            
            result = {"completed": False}
            
            def restore_callback(status_data):
                status, data = status_data
                result["completed"] = True
                if status == "success":
                    print(f"✅ Restored to {current_mode} mode")
                else:
                    print(f"❌ Failed to restore: {data}")
            
            exchange.setPositionMode(current_mode, restore_callback)
            
            # Wait for completion
            start_time = time.time()
            while not result["completed"] and (time.time() - start_time) < timeout:
                time.sleep(0.01)
    
    print("\n=== Position Mode Test Complete ===")

if __name__ == "__main__":
    test_position_mode()