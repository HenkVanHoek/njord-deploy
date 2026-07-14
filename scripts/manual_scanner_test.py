# scripts/run_scanner_test.py
import os
import sys

# This block must come before the 'src' import
# to ensure the script can find the necessary modules.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_path = os.path.join(project_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from src.pi_scanner import PiScanner  # noqa: E402


def main():
    """
    A simple command-line script to test the PiScanner functionality.
    """
    print("--- PiScanner Test Script ---")

    # 1. Detect Subnet
    print("\n--- Step 1: Detecting local subnet ---")
    detected_subnet = PiScanner.detect_subnet()
    if detected_subnet:
        print(f"Automatically detected subnet: {detected_subnet}")
    else:
        print("Could not automatically detect subnet.")
        detected_subnet = "192.168.1.0/24"  # Fallback
        print(f"Using fallback subnet: {detected_subnet}")

    # 2. Get User Input for Scan
    target_subnet = (
        input(f"Enter the subnet to scan (default: {detected_subnet}): ").strip()
        or detected_subnet
    )

    # 3. Run Network Scan
    print(f"\n--- Step 2: Scanning {target_subnet} for Raspberry Pis ---")
    try:
        found_pis = PiScanner.scan(target_subnet)
    except Exception as e:
        print(f"An error occurred during the scan: {e}")
        return

    if not found_pis:
        print("No Raspberry Pi devices found on the network.")
        return

    print(f"\nFound {len(found_pis)} potential Raspberry Pi(s):")
    for i, pi in enumerate(found_pis, 1):
        print(f"  {i}. IP: {pi['ip']}, MAC: {pi['mac']}")

    # 4. Get SSH Credentials
    print("\n--- Step 3: Retrieving Device Details via SSH ---")
    ssh_user = input("Enter SSH username to test with (e.g., 'pi'): ").strip()
    # Use a more secure way to get password if this were a real tool
    ssh_pass = input("Enter SSH password (or leave blank for key auth): ").strip()

    # 5. Retrieve and Display Details
    successful_devices = []
    failed_devices = []

    for pi in found_pis:
        print(f"\nConnecting to {pi['ip']}...")
        details = PiScanner.get_device_details(pi["ip"], ssh_user, ssh_pass or None)

        if details:
            successful_devices.append({"ip": pi["ip"], "details": details})
        else:
            failed_devices.append(pi)

    # 6. Print Summary
    print("\n\n--- Scan and Detail Retrieval Complete ---")

    if successful_devices:
        print("\n✅ Successfully retrieved details for:")
        for device in successful_devices:
            details = device["details"]
            print(f"\n  Device at {device['ip']}:")
            print(f"    - Model: {details.get('model', 'N/A')}")
            print(f"    - RAM: {details.get('ram', 'N/A')}")
            print(f"    - Serial: {details.get('serial', 'N/A')}")
            print("    - Disks:")
            for disk in details.get("disks", []):
                print(f"      - {disk.get('name')}: {disk.get('size')}")

    if failed_devices:
        print("\n❌ Failed to retrieve details for:")
        for device in failed_devices:
            print(f"  - IP: {device['ip']}, MAC: {device['mac']}")


if __name__ == "__main__":
    main()
