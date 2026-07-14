# test_scanner.py

import logging
import os
import sys

from dotenv import load_dotenv

# Ensure the src directory is in the search path
project_root = os.path.abspath(os.path.dirname(__file__))
src_path = os.path.join(project_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from pi_scanner import PiScanner  # noqa: E402

# Set up basic logging to see detailed messages
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def main():
    """Runs the PiScanner in a controlled, isolated environment."""
    print("--- Starting PiScanner Test ---")

    # Load environment variables from the .env file
    load_dotenv()

    # Retrieve credentials from environment variables
    pi_username = os.getenv("TEST_PI_USERNAME")
    pi_password = os.getenv("TEST_PI_PASSWORD")

    if not pi_username or not pi_password:
        print("\n!!! ACTION REQUIRED !!!")
        print(
            "Please ensure TEST_PI_USERNAME and TEST_PI_PASSWORD "
            "are set in your .env file."
        )
        return

    try:
        # 1. Initialize the scanner
        print(f"\nInitializing scanner for user: {pi_username}...")
        scanner = PiScanner(username=pi_username, password=pi_password)

        # 2. Run the scan with auto-detection
        print("Starting network scan (auto-detecting subnet)...")
        hosts, messages, error, detection_info = scanner.scan()

        # 3. Print the results
        print("\n--- SCAN COMPLETE ---")

        print("\n[Detection Info]")
        print(f"  Success: {detection_info.get('success')}")
        print(f"  Method Used: {detection_info.get('method_used')}")
        print(f"  Detected IP: {detection_info.get('detected_ip')}")
        print(f"  Subnet Scanned: {detection_info.get('subnet')}")

        print("\n[Messages]")
        if messages:
            for msg in messages:
                print(f"  - {msg}")
        else:
            print("  No messages.")

        print("\n[Detected Hosts]")
        if hosts:
            for host in hosts:
                print(f"  - {host}")
        else:
            print("  No hosts found.")

        if error:
            print("\n[Error Reported]")
            print(f"  - {error}")

    except Exception:
        print("\n--- AN UNEXPECTED ERROR OCCURRED ---")
        logging.exception("The test script failed unexpectedly.")


if __name__ == "__main__":
    main()
