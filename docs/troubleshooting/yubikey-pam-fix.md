# YubiKey Authentication Setup and Troubleshooting Guide (Ubuntu 24.04 LTS)

This document details the configuration steps and critical fixes required to enable FIDO/U2F authentication (YubiKey 5 Series or Bio) for system login and `sudo` commands on Ubuntu 24.04 (Noble Numbat).

This guide specifically addresses the persistent **`E: Unable to locate package`** error and the **`Permissions 0664`** security warning encountered during setup.

---

## 1. Initial Setup and Repository Fixes

The primary PAM module (`libpam-fido2`) was inaccessible due to a persistent bug in the Ubuntu 24.04 Universe repository index. We use the alternative module, `libpam-u2f`, after ensuring the system repositories are connected.

### 1.1 Restore Primary Repositories (Mandatory Fix)

If you encounter persistent `E: Unable to locate package` errors, your primary source list is likely corrupted. Run these commands to restore the base repositories before attempting installation:

    sudo mv /etc/apt/sources.list.d/ubuntu.sources /tmp/
    sudo add-apt-repository "deb http://nl.archive.ubuntu.com/ubuntu/ noble main restricted universe multiverse"
    sudo add-apt-repository "deb http://nl.archive.ubuntu.com/ubuntu/ noble-updates main restricted universe multiverse"
    sudo add-apt-repository "deb http://nl.archive.ubuntu.com/ubuntu/ noble-security main restricted universe multiverse"

### 1.2 Install Required Packages

Install the necessary YubiKey management tool and the functional PAM module:

    sudo apt update
    sudo apt install yubikey-manager libpam-u2f

---

## 2. Key Registration and Credential Generation

We generate the cryptographic key mapping file (`u2f_keys`) which links your YubiKey to your Linux user account.

### 2.1 Create Configuration Directory

    mkdir -p ~/.config/Yubico

### 2.2 Generate and Save Credentials

The `pamu2fcfg` command reads your YubiKey and generates a unique credential string.

> **IMPORTANT:** You must enter your FIDO2/YubiKey PIN when prompted, and then touch the gold circle on your YubiKey.

    pamu2fcfg > ~/.config/Yubico/u2f_keys

### 2.3 Add Secondary/Backup Key (Highly Recommended)

To prevent being locked out, add your second YubiKey to the same file (note the `>>` flag to append, and the `-n` flag):

1.  Insert the backup key.
2.  Run the command:

    pamu2fcfg -n >> ~/.config/Yubico/u2f_keys

---

## 3. Critical Security Fix (Permissions)

The `pam_u2f` module rejects the key file if its permissions are too open (`0664`). This is a common failure point that must be fixed manually.

    chmod 0644 /home/<username>/.config/Yubico/u2f_keys

> **Note:** Replace `<username>` with your actual username (`hvhoek`) throughout the configuration, as the `~` notation can fail in the PAM context.

---

## 4. Final PAM Configuration (`common-auth`)

Edit the core authentication stack file to enable the YubiKey as the primary login method with password as a fallback.

1.  Open the file:

    sudo nano /etc/pam.d/common-auth

2.  Locate the section starting with `# here are the per-package modules (the "Primary" block)`.
3.  **Replace the existing logic** with the following robust block. This ensures the YubiKey is checked first, and the rest of the rules (including password, `pam_sss.so`, etc.) only run if the key is not present or authentication fails.

**Find and replace the relevant lines (including `pam_unix.so` and `pam_sss.so`) with this corrected block:**

    # here are the per-package modules (the "Primary" block)
    # START YUBIKEY/U2F CONFIGURATION
    # Rule 1: Key Check (sufficient means success skips password, failure falls through)
    auth    sufficient    pam_u2f.so    authfile=/home/<username>/.config/Yubico/u2f_keys nopinprompt
    # END YUBIKEY/U2F CONFIGURATION
    # Rule 2: Traditional Password Check (Adjusted jump logic)
    auth    [success=2 default=ignore]      pam_unix.so nullok
    auth    [success=1 default=ignore]      pam_sss.so use_first_pass
    ...

---

## 5. Verification

In a new terminal, execute a `sudo` command. The terminal should immediately wait for you to touch the YubiKey.

    sudo ls /

If the key is touched and accepted, the command runs instantly. If no key is present or touched, the system will fall through to ask for your password.

This completes the setup and fixes all known issues encountered during this process.
