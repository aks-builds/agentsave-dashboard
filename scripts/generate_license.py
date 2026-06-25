#!/usr/bin/env python
# scripts/generate_license.py — internal use only, not shipped in package
import argparse
import time
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from pathlib import Path

parser = argparse.ArgumentParser(description="Generate an AgentSave license key")
parser.add_argument("--tier", choices=["free", "pro", "enterprise"], required=True)
parser.add_argument("--seats", type=int, default=1)
parser.add_argument("--org", required=True)
parser.add_argument("--email", required=True)
parser.add_argument("--days", type=int, default=365)
parser.add_argument("--private-key", default="scripts/private.pem")
args = parser.parse_args()

with open(args.private_key, "rb") as f:
    private_key = serialization.load_pem_private_key(f.read(), password=None, backend=default_backend())

payload = {
    "tier": args.tier,
    "seats": args.seats,
    "exp": int(time.time()) + args.days * 86400,
    "iss": "agentsave",
    "org": args.org,
    "email": args.email,
}
token = jwt.encode(payload, private_key, algorithm="RS256")
print(token)
