# Building a Sovereign Home Server: Lessons Learned

This document provides a summary of the architectural decisions, optimizations, and lessons learned from deploying a resource-intensive sovereign self-hosting stack on a Raspberry Pi 5. It is based on the article published on DEV Community.

## Article Reference

- **Title:** Building a Sovereign Home Server: Lessons Learned Running Nextcloud, Euro-Office, and Frigate on a Raspberry Pi 5
- **Author:** Henk van Hoek
- **URL:** [Read the full article on DEV.to](https://dev.to/henk_van_hoek/building-a-sovereign-home-server-lessons-learned-running-nextcloud-euro-office-and-frigate-on-a-1kbc)

## Key Technical Decisions and Lessons

### 1. Memory Optimization (ZRAM)
Running services like Nextcloud, Euro-Office (document server), and Frigate (NVR) simultaneously can easily saturate the 8GB of RAM on a Raspberry Pi 5.
- **Problem:** Traditional swap on SD cards or SSDs is too slow and causes premature wear of the storage media.
- **Solution:** Configure ZRAM (compressed swap space in RAM). This dynamically compresses unused memory segments, allowing the system to handle memory spikes efficiently without hitting physical disk swap.

### 2. Offloading AI Workloads (Google Coral TPU)
Real-time object detection in computer vision applications like Frigate is highly compute-intensive.
- **Problem:** Running object detection on the Raspberry Pi 5 CPU will pin all four cores at 100% CPU utilization, causing other services (such as databases and web servers) to become unresponsive.
- **Solution:** Offloading object detection to a dedicated hardware accelerator, specifically a Google Coral TPU, is non-negotiable. This keeps CPU cycles free for Nextcloud database queries and general OS operations.

### 3. Software Deployment Configurations
- **Nextcloud and Euro-Office:** Seamless collaborative office suites require precise container configurations. For example, the JWT_SECRET (JSON Web Token Secret) for HS256 encryption between Nextcloud and Euro-Office must be exactly 32 characters long to avoid authentication failures.
- **Private Mesh Networking:** Utilizing tools like Headscale enables secure, private remote access without exposing services directly to the public internet.

### 4. Network and DNS Architecture
Running local security services (such as AdGuard Home) alongside self-hosted application stacks requires careful local DNS routing to prevent resolution loops and ensure smooth internal connectivity.

## System Performance Under Load
During stress testing (running four active security cameras and a live backup simultaneously):
- **CPU Load:** Stable at approximately 67%.
- **Operating Temperature:** Maintained at 61 degrees Celsius.
- **Result:** The Raspberry Pi 5 stands out as a highly viable, energy-efficient platform for hosting a complete private cloud stack when configured with proper offloading and memory optimizations.
