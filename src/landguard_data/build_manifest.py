"""Generates dataset release manifests and file checksum registers."""

import os
import json
import hashlib
from typing import Dict, Any, List


def calculate_file_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def generate_manifest(
    data_dir: str,
    output_path: str,
    metadata: Dict[str, Any] = None
) -> Dict[str, Any]:
    file_records = []
    
    for root, _, files in os.walk(data_dir):
        for f in files:
            full_p = os.path.join(root, f)
            rel_p = os.path.relpath(full_p, data_dir)
            sha = calculate_file_sha256(full_p)
            size_b = os.path.getsize(full_p)
            file_records.append({
                "path": rel_p.replace("\\", "/"),
                "sha256": sha,
                "size_bytes": size_b
            })
            
    manifest = {
        "manifest_version": "1.0.0",
        "total_files": len(file_records),
        "metadata": metadata or {},
        "files": file_records
    }
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        
    return manifest
