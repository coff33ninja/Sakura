# Sakura Hardening Guide

This guide provides actionable steps to reduce risk when running Sakura. Because Sakura is a powerful AI agent with system-level capabilities, proper hardening is essential.

> **TL;DR:** Run Sakura in a VM, don't store sensitive files where it can access them, actually read scripts before running them, and don't trust it blindly.

---

## Risk Assessment

Before hardening, understand what you're protecting against:

| Risk Level | User Profile | Recommended Hardening |
|------------|--------------|----------------------|
| **Low** | Developer testing locally, no sensitive data | Level 1 (Basic) |
| **Medium** | Regular use, some sensitive files on system | Level 2 (Network Isolation) |
| **High** | Sensitive data, professional use | Level 3 (Sandboxed) |
| **Critical** | Highly sensitive environment | Don't use Sakura, or Level 4+ |

---

## Level 1: Basic Precautions

**Time to implement:** 10 minutes
**Protection:** Reduces accidental damage and casual misuse

### 1.1 Run as Limited User

Never run Sakura as Administrator.

```powershell
# Check if running as admin (should return False)
([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
```

### 1.2 Separate User Account (Recommended)

Create a dedicated Windows user for Sakura:

```powershell
# Create new local user (run as admin, then switch to this user for Sakura)
net user SakuraUser /add
# Set password when prompted

# Log in as SakuraUser to run Sakura
# This limits file access to only what SakuraUser can see
```

### 1.3 Move Sensitive Files

Sakura can search and read any file your user can access. Move sensitive files:

| File Type | Action |
|-----------|--------|
| Password managers | Keep database on encrypted drive, unmount when using Sakura |
| Financial documents | Move to separate user profile or encrypted container |
| Private keys (SSH, crypto) | Store in hardware key or encrypted container |
| Work documents | Use separate user account |

### 1.4 Use Unique API Keys

Create Gemini API keys specifically for Sakura:

1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Create new API key labeled "Sakura"
3. If compromised, revoke only this key
4. Don't reuse keys from other projects

### 1.5 Actually Read Scripts

This is the most important step. When Sakura generates a script:

```
⚠️ STOP. READ THE SCRIPT. UNDERSTAND IT.

Ask yourself:
- What files does this touch?
- Does it access the network?
- Does it modify system settings?
- Does it create scheduled tasks?
- Does it download anything?
- Could this damage my system?
```

### 1.6 Regular Backups

Back up Sakura's source to detect self-modification:

```powershell
# Create backup of Sakura source
Copy-Item -Path "C:\path\to\sakura" -Destination "C:\backups\sakura-$(Get-Date -Format 'yyyyMMdd')" -Recurse

# Or use git
cd C:\path\to\sakura
git status  # Check for unexpected changes
git diff    # See what changed
```

---

## Level 2: Network Isolation

**Time to implement:** 30 minutes
**Protection:** Prevents data exfiltration, limits external communication

### 2.1 Windows Firewall Rules

Block Python from accessing unexpected destinations:

```powershell
# Run as Administrator

# First, find your Python path
$pythonPath = (Get-Command python).Source
# Or for venv: $pythonPath = "C:\path\to\sakura\.venv\Scripts\python.exe"

# Block all outbound by default for Python
New-NetFirewallRule -DisplayName "Block Python Outbound" `
    -Direction Outbound `
    -Program $pythonPath `
    -Action Block

# Allow specific destinations (Gemini API)
New-NetFirewallRule -DisplayName "Allow Python to Gemini" `
    -Direction Outbound `
    -Program $pythonPath `
    -RemoteAddress "142.250.0.0/16" `  # Google IP range (approximate)
    -Action Allow

# Allow DNS
New-NetFirewallRule -DisplayName "Allow Python DNS" `
    -Direction Outbound `
    -Program $pythonPath `
    -RemotePort 53 `
    -Protocol UDP `
    -Action Allow
```

**Note:** Google's IP ranges change. This is approximate. Consider using a proxy instead.

### 2.2 DNS Monitoring

Monitor what domains Sakura tries to access:

```powershell
# Enable DNS Client logging (run as admin)
wevtutil sl Microsoft-Windows-DNS-Client/Operational /e:true

# View DNS queries
Get-WinEvent -LogName "Microsoft-Windows-DNS-Client/Operational" | 
    Where-Object { $_.Message -like "*python*" } |
    Select-Object TimeCreated, Message
```

### 2.3 Proxy Configuration

Route Sakura traffic through a monitoring proxy:

```powershell
# Set proxy for Python (in .env or environment)
$env:HTTP_PROXY = "http://127.0.0.1:8080"
$env:HTTPS_PROXY = "http://127.0.0.1:8080"

# Use tools like mitmproxy, Fiddler, or Burp Suite to inspect traffic
```

---

## Level 3: Sandboxed Execution

**Time to implement:** 1-2 hours
**Protection:** Full isolation from host system

### 3.1 Virtual Machine (Recommended)

The most effective isolation method.

#### Option A: Hyper-V (Windows Pro/Enterprise)

```powershell
# Enable Hyper-V (run as admin, requires reboot)
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All

# Create VM via Hyper-V Manager
# - Allocate 4GB+ RAM
# - 50GB+ disk
# - Install Windows
# - Install Sakura in VM only
```

#### Option B: VirtualBox (Free, any Windows)

1. Download [VirtualBox](https://www.virtualbox.org/)
2. Create Windows VM
3. Install Sakura in VM
4. **Important:** Don't enable shared folders with sensitive host data

#### VM Best Practices

| Setting | Recommendation |
|---------|----------------|
| Shared folders | Disable or read-only, no sensitive data |
| Clipboard sharing | Disable for maximum security |
| Network | NAT (isolated) or Bridged (if needed) |
| Snapshots | Take clean snapshot before use |
| USB passthrough | Disable unless needed for microphone |

### 3.2 Windows Sandbox (Quick, Disposable)

For testing only — doesn't persist between sessions.

```powershell
# Enable Windows Sandbox (Windows Pro/Enterprise)
Enable-WindowsOptionalFeature -Online -FeatureName "Containers-DisposableClientVM" -All

# Create Sandbox config file: sakura.wsb
```

```xml
<!-- sakura.wsb -->
<Configuration>
  <MappedFolders>
    <MappedFolder>
      <HostFolder>C:\path\to\sakura</HostFolder>
      <SandboxFolder>C:\Sakura</SandboxFolder>
      <ReadOnly>false</ReadOnly>
    </MappedFolder>
  </MappedFolders>
  <AudioInput>Enable</AudioInput>
  <Networking>Enable</Networking>
  <MemoryInMB>4096</MemoryInMB>
</Configuration>
```

Double-click `sakura.wsb` to launch isolated environment.

### 3.3 Docker/WSL (Advanced)

For Linux-comfortable users:

```dockerfile
# Dockerfile for Sakura (experimental)
FROM python:3.12-slim

# Install audio dependencies
RUN apt-get update && apt-get install -y \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Run with limited capabilities
USER nobody
CMD ["python", "main.py"]
```

```powershell
# Build and run
docker build -t sakura .
docker run --rm -it `
    --device /dev/snd `
    -v ${PWD}/.env:/app/.env:ro `
    sakura
```

---

## Level 4: Monitoring & Alerting

**Time to implement:** 2-4 hours
**Protection:** Detect suspicious activity in real-time

### 4.1 Sysmon Installation

[Sysmon](https://docs.microsoft.com/en-us/sysinternals/downloads/sysmon) provides detailed Windows event logging.

```powershell
# Download Sysmon from Sysinternals
# Install with config
sysmon64.exe -accepteula -i sysmon-config.xml
```

### 4.2 Sysmon Configuration for Sakura

```xml
<!-- sysmon-config.xml -->
<Sysmon schemaversion="4.90">
  <EventFiltering>
    <!-- Log all process creation by Python -->
    <ProcessCreate onmatch="include">
      <Image condition="contains">python</Image>
    </ProcessCreate>
    
    <!-- Log file creation in sensitive locations -->
    <FileCreate onmatch="include">
      <TargetFilename condition="contains">\Startup\</TargetFilename>
      <TargetFilename condition="contains">\scripts\</TargetFilename>
      <TargetFilename condition="end with">.ps1</TargetFilename>
      <TargetFilename condition="end with">.bat</TargetFilename>
      <TargetFilename condition="end with">.py</TargetFilename>
    </FileCreate>
    
    <!-- Log network connections by Python -->
    <NetworkConnect onmatch="include">
      <Image condition="contains">python</Image>
    </NetworkConnect>
    
    <!-- Log registry modifications -->
    <RegistryEvent onmatch="include">
      <TargetObject condition="contains">CurrentVersion\Run</TargetObject>
    </RegistryEvent>
    
    <!-- Log scheduled task creation -->
    <ProcessCreate onmatch="include">
      <CommandLine condition="contains">schtasks</CommandLine>
    </ProcessCreate>
  </EventFiltering>
</Sysmon>
```

### 4.3 PowerShell Alerting Script

```powershell
# monitor-sakura.ps1 - Run in separate terminal

$logName = "Microsoft-Windows-Sysmon/Operational"

# Watch for suspicious events
Get-WinEvent -LogName $logName -FilterXPath "*[System[EventID=1 or EventID=3 or EventID=11]]" -MaxEvents 1 | 
    ForEach-Object {
        $event = $_
        
        # Alert on network connections to unexpected IPs
        if ($event.Id -eq 3) {
            $destIP = $event.Properties[14].Value
            if ($destIP -notmatch "^(142\.250\.|10\.|192\.168\.|127\.)") {
                Write-Host "⚠️ ALERT: Python connected to $destIP" -ForegroundColor Red
            }
        }
        
        # Alert on script creation
        if ($event.Id -eq 11) {
            $filename = $event.Properties[5].Value
            if ($filename -match "\.(ps1|bat|py|vbs)$") {
                Write-Host "⚠️ ALERT: Script created: $filename" -ForegroundColor Yellow
            }
        }
        
        # Alert on persistence mechanisms
        if ($event.Id -eq 1) {
            $cmdline = $event.Properties[10].Value
            if ($cmdline -match "schtasks|startup|CurrentVersion\\Run") {
                Write-Host "🚨 CRITICAL: Persistence mechanism detected!" -ForegroundColor Red
                Write-Host $cmdline
            }
        }
    }
```

### 4.4 File Integrity Monitoring

Detect if Sakura modifies its own source:

```powershell
# Create baseline hashes
Get-ChildItem -Path "C:\path\to\sakura" -Recurse -Include "*.py" | 
    ForEach-Object { 
        [PSCustomObject]@{
            Path = $_.FullName
            Hash = (Get-FileHash $_.FullName -Algorithm SHA256).Hash
        }
    } | Export-Csv "sakura-baseline.csv"

# Check for modifications
$baseline = Import-Csv "sakura-baseline.csv"
$baseline | ForEach-Object {
    $current = (Get-FileHash $_.Path -Algorithm SHA256 -ErrorAction SilentlyContinue).Hash
    if ($current -ne $_.Hash) {
        Write-Host "⚠️ MODIFIED: $($_.Path)" -ForegroundColor Red
    }
}
```

---

## Level 5: Code Modifications

**Time to implement:** Variable
**Protection:** Enforce restrictions at code level

### 5.1 Path Restriction Module

Add to Sakura source:

```python
# modules/security.py

import os
from pathlib import Path
from typing import List

class SecurityError(Exception):
    pass

# Allowed write locations
ALLOWED_WRITE_PATHS: List[Path] = [
    Path.home() / "Documents" / "Sakura",
]

# Blocked paths (never allow)
BLOCKED_PATHS: List[str] = [
    "sakura",  # Own source directory
    ".git",
    "Windows",
    "System32",
    "Program Files",
]

def validate_write_path(path: str) -> bool:
    """Check if path is safe to write to."""
    resolved = Path(path).resolve()
    
    # Check blocked paths
    path_str = str(resolved).lower()
    for blocked in BLOCKED_PATHS:
        if blocked.lower() in path_str:
            raise SecurityError(f"Write to blocked path: {path}")
    
    # Check allowed paths
    for allowed in ALLOWED_WRITE_PATHS:
        try:
            resolved.relative_to(allowed)
            return True
        except ValueError:
            continue
    
    raise SecurityError(f"Write to non-allowed path: {path}")

def validate_network_destination(host: str) -> bool:
    """Check if network destination is allowed."""
    ALLOWED_HOSTS = [
        "generativelanguage.googleapis.com",
        "api.duckduckgo.com",
    ]
    
    if host not in ALLOWED_HOSTS:
        raise SecurityError(f"Network access to non-allowed host: {host}")
    
    return True
```

### 5.2 Script Execution Confirmation

```python
# Add to script execution flow

import hashlib

def execute_script_with_confirmation(script_path: str) -> str:
    """Require explicit confirmation before script execution."""
    
    with open(script_path, 'r') as f:
        content = f.read()
    
    # Calculate hash for verification
    script_hash = hashlib.sha256(content.encode()).hexdigest()[:8]
    
    print("\n" + "="*60)
    print("⚠️  SCRIPT EXECUTION REQUEST")
    print("="*60)
    print(f"File: {script_path}")
    print(f"Hash: {script_hash}")
    print("-"*60)
    print(content)
    print("-"*60)
    print(f"\nTo execute, type the hash: {script_hash}")
    
    confirmation = input("Confirm: ").strip()
    
    if confirmation != script_hash:
        return "Execution cancelled - hash mismatch"
    
    # Actually execute
    # ... execution logic ...
```

### 5.3 Action Classification

```python
# modules/action_classifier.py

from enum import Enum
from typing import Dict, Any

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

ACTION_RISK_LEVELS: Dict[str, RiskLevel] = {
    # Low risk - read-only, reversible
    "get_system_info": RiskLevel.LOW,
    "search_files": RiskLevel.LOW,
    "get_clipboard": RiskLevel.LOW,
    
    # Medium risk - writes but limited scope
    "create_note": RiskLevel.MEDIUM,
    "set_reminder": RiskLevel.MEDIUM,
    "write_file": RiskLevel.MEDIUM,
    
    # High risk - system changes
    "execute_script": RiskLevel.HIGH,
    "run_command": RiskLevel.HIGH,
    "delete_file": RiskLevel.HIGH,
    
    # Critical - persistence, privilege, network
    "create_scheduled_task": RiskLevel.CRITICAL,
    "modify_registry": RiskLevel.CRITICAL,
    "download_file": RiskLevel.CRITICAL,
}

def get_action_risk(action: str) -> RiskLevel:
    return ACTION_RISK_LEVELS.get(action, RiskLevel.HIGH)

def requires_confirmation(action: str) -> bool:
    risk = get_action_risk(action)
    return risk in (RiskLevel.HIGH, RiskLevel.CRITICAL)
```

---

## Quick Reference

### Minimum Recommended Setup

| User Type | Minimum Hardening |
|-----------|-------------------|
| Developer testing | Level 1 + read scripts |
| Personal use | Level 1 + Level 2 (firewall) |
| Any sensitive data | Level 3 (VM) |
| Professional/work | Level 3 + Level 4 |

### Red Flags to Watch For

| Indicator | Concern |
|-----------|---------|
| Scripts you didn't request | Possible prompt injection |
| Network connections to unknown IPs | Data exfiltration |
| Files modified in Sakura directory | Self-modification |
| Scheduled tasks created | Persistence |
| Registry Run keys modified | Persistence |
| UAC prompts from Sakura | Privilege escalation attempt |

### Emergency Response

If you suspect compromise:

```powershell
# 1. Kill Sakura immediately
taskkill /F /IM python.exe

# 2. Disconnect network
# (physically or via settings)

# 3. Check for persistence
schtasks /query /fo LIST | findstr /i sakura
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Run"

# 4. Review recent activity
type sakura_memory.json | findstr action_log

# 5. Restore from backup or clean install
```

---

## Additional Resources

- [SECURITY.md](SECURITY.md) — Full security policy and threat model
- [ETHICS_AND_ACCESSIBILITY.md](ETHICS_AND_ACCESSIBILITY.md) — Ethical guidelines
- [CONTRIBUTING.md](CONTRIBUTING.md) — Security-focused contribution guidelines

---

*Stay safe. Stay paranoid. Trust but verify.*
