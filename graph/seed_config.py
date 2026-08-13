"""
Seed configuration for the prototype graph.

WHY THIS IS A FIXED LIST (see docs/decisions/001-seed-scope.md):
    This prototype deliberately scopes to 3 groups and 13 techniques
    rather than ingesting all of ATT&CK. The techniques were chosen to
    (a) form a coherent, explainable kill chain and (b) overlap across
    all three groups so group-comparison queries have real data behind
    them. Every technique here was verified against the live MITRE
    ATT&CK STIX dataset (data/raw/enterprise-attack.json) as actually
    used by these groups - see graph/build_graph.py.
"""

SEED_GROUPS = {
    "APT29": "intrusion-set--899ce53f-13a0-479b-a0e4-67d46e241542",   # G0016
    "APT28": "intrusion-set--bef4c620-0787-42a8-a96d-b7eb6e85917c",   # G0007
    "Lazarus Group": "intrusion-set--c93fccb1-e8e8-42cf-ae33-2ad1d183913a",  # G0032
}

# Ordered roughly by kill-chain position - not enforced, just readable.
SEED_TECHNIQUES = [
    "T1566.001",  # Spearphishing Attachment      - initial-access
    "T1204.002",  # Malicious File                - execution
    "T1059.001",  # PowerShell                     - execution
    "T1547.001",  # Registry Run Keys/Startup      - persistence
    "T1078",      # Valid Accounts                 - persistence/priv-esc
    "T1003.002",  # Security Account Manager       - credential-access
    "T1057",      # Process Discovery              - discovery
    "T1083",      # File and Directory Discovery   - discovery
    "T1021.001",  # Remote Desktop Protocol        - lateral-movement
    "T1071.001",  # Web Protocols (C2)             - command-and-control
    "T1105",      # Ingress Tool Transfer          - command-and-control
    "T1560.001",  # Archive via Utility            - collection
    "T1074.002",  # Remote Data Staging            - collection
]
