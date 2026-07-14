# Design Decision Document: SSH Security Hardening

**Status:** Approved
**Date:** 2026-03-08
**Subject:** Transition to Paramiko and Ed25519 Key-Based Authentication

---

## 1. Context and Problem Statement

The initial implementation used `sshpass` for remote orchestration. This presented several security and operational risks:
* **Cleartext Passwords:** Credentials were often handled in memory or environment variables in a way that was vulnerable to process sniffing.
* **Legacy Dependency:** `sshpass` is a non-standard tool that added overhead to the release pipeline.
* **Weak Authentication:** Reliance on passwords made the system vulnerable to brute-force attacks on the local network.

## 2. Decision: Ed25519 Key-Based Authentication

We decided to implement a modern SSH strategy using the `cryptography` and `paramiko` libraries.

### 2.1 Technical Specifications
* **Key Type:** Ed25519 (Edwards-curve Digital Signature Algorithm).
* **Library:** `cryptography.hazmat` for key generation and `paramiko` for transport.
* **Storage:** Keys are generated during the `SetupManager` initialization and stored in the user data directory with restricted filesystem permissions (`0600`).



---

## 3. Implementation Details

### 3.1 Automated Key Management
The `SetupManager` now checks for the existence of an identity key upon startup. If missing, it generates a new Ed25519 pair.

### 3.2 SSH Hardening Logic
* **Missing Host Key Policy:** Implemented `paramiko.AutoAddPolicy()` for initial discovery, with plans to transition to strict host checking.
* **No Password Fallback:** Once the key is deployed, password authentication is disabled in the `DeploymentManager` to enforce key-only access.
* **Environment Detection:** Added logic to detect WSL (Windows Subsystem for Linux) environments to handle specific SSH socket behaviors.

## 4. Consequences

### 4.1 Positive
* **Improved Security:** Ed25519 provides high security with smaller key sizes and better performance than RSA.
* **Zero Interaction:** Deployments no longer require manual password entry once the initial key is pushed.
* **Standard Compliance:** Aligns with modern security best practices for IoT and self-hosting environments.

### 4.2 Negative
* **Initial Bootstrap:** Requires a one-time password-based connection to "seed" the public key to the target device.
