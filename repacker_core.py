"""
RWMod Repacker Core - WinRAR Extraction Breaker
- Local header sizes set to 0 → WinRAR extracts empty files
- Decoy central directory & EOCD wiped → 7-Zip sees nothing
- Real ZIP valid at the end → game loads normally
"""

import os, io, random, hashlib, zipfile, tempfile, mmap
from typing import Optional, Callable

ZIP_MMAP_THRESHOLD = 50 * 1024 * 1024

def corrupt_local_header_sizes(zip_bytes: bytes) -> bytes:
    """Set compressed and uncompressed size in local headers to 0."""
    result = bytearray(zip_bytes)
    pos = 0
    sig = b'PK\x03\x04'
    while True:
        pos = result.find(sig, pos)
        if pos == -1:
            break
        # compressed size at pos+18, uncompressed at pos+22 (both 4 bytes)
        result[pos+18:pos+26] = b'\x00\x00\x00\x00\x00\x00\x00\x00'
        pos += 4
    return bytes(result)

def build_dummy_zip_layer(seed: bytes) -> bytes:
    rng = random.Random(int.from_bytes(seed[:8], "big"))
    dummy_io = io.BytesIO()
    with zipfile.ZipFile(dummy_io, "w", zipfile.ZIP_DEFLATED) as dz:
        folder = "ModFiles_Protected/Secure_Runtime_Environment/"
        dz.writestr(f"{folder}security_manifest.cfg",
                    b"// Error: Cryptographic Handshake Failed.\n// Access Denied.")
        dz.writestr(f"{folder}metadata.json",
                    f"{{'status': 'corrupted', 'seed': '{seed.hex()[:16]}'}}".encode())
    return dummy_io.getvalue()

def wipe_decoy_central_directory(payload: bytes, decoy_len: int) -> bytes:
    sig = b'PK\x01\x02'
    result = bytearray(payload)
    pos = 0
    while True:
        pos = result.find(sig, pos, decoy_len)
        if pos == -1:
            break
        result[pos:pos+4] = b'\x00\x00\x00\x00'
        pos += 4
    return bytes(result)

def wrap_with_sandwich_sandbox(real_zip_bytes: bytes, seed: bytes) -> bytes:
    rng = random.Random(int.from_bytes(seed[8:16], "big"))
    decoy_layer = build_dummy_zip_layer(seed)
    decoy_len = len(decoy_layer)
    barrier_sig = b"\x7F\x46\x41\x55\x58\x5F\x43\x4F\x52\x52\x55\x50\x54"
    barrier_padding = os.urandom(rng.randint(512, 2048))
    custom_barrier = barrier_sig + barrier_padding
    chaff = os.urandom(135168)
    payload = decoy_layer + custom_barrier + chaff + real_zip_bytes
    payload = wipe_decoy_central_directory(payload, decoy_len)
    decoy_eocd = payload.rfind(b'PK\x05\x06', 0, decoy_len)
    if decoy_eocd != -1:
        payload = payload[:decoy_eocd] + b'\x00\x00\x00\x00' + payload[decoy_eocd+4:]
    return payload

def zip_folder_hybrid(folder_path: str, temp_zip_path: str,
                      progress: Optional[Callable[[float], None]] = None) -> None:
    files = []
    for root, _, fs in os.walk(folder_path):
        for f in fs:
            files.append(os.path.join(root, f))
    os.makedirs(os.path.dirname(temp_zip_path) or ".", exist_ok=True)
    with zipfile.ZipFile(temp_zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for i, path in enumerate(files):
            arc = os.path.relpath(path, folder_path)
            size = os.path.getsize(path)
            if size > ZIP_MMAP_THRESHOLD:
                with open(path, "rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                    zf.writestr(arc, mm)
            else:
                zf.write(path, arc)
            if progress:
                progress((i+1)/max(1, len(files)))

def pack_as_rwmod(folder_path: str, rwmod_path: str,
                  progress_callback: Optional[Callable[[float], None]] = None) -> None:
    """Main repack function. progress_callback receives value 0..1."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        temp_zip = tmp.name
    try:
        # Step 1: create ZIP
        if progress_callback: progress_callback(0.1)
        zip_folder_hybrid(folder_path, temp_zip, progress=lambda p: progress_callback and progress_callback(0.1 + p*0.4))
        with open(temp_zip, "rb") as f:
            zip_bytes = f.read()
        # Step 2: corrupt local headers
        if progress_callback: progress_callback(0.6)
        corrupted_zip = corrupt_local_header_sizes(zip_bytes)
        # Step 3: generate seed
        seed = hashlib.sha3_512(zip_bytes).digest()
        # Step 4: wrap in sandbox
        if progress_callback: progress_callback(0.7)
        final_payload = wrap_with_sandwich_sandbox(corrupted_zip, seed)
        # Step 5: write output
        os.makedirs(os.path.dirname(rwmod_path) or ".", exist_ok=True)
        with open(rwmod_path, "wb") as f:
            f.write(final_payload)
        if progress_callback: progress_callback(1.0)
    finally:
        try: os.remove(temp_zip)
        except: pass