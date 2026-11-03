#!/usr/bin/env python3
"""Zip Tinned Fish Passport source (stamps + site source, no .git/src/img) for Drive backup."""
import os, sys, zipfile
out = sys.argv[1] if len(sys.argv) > 1 else "/workspace/passport-drive-backup.zip"
root = "/workspace"
skip = {"passport-site/.git", "passport-site/src", "passport-site/img"}
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for top in ("stamps", "passport-site"):
        for d, dirs, files in os.walk(os.path.join(root, top)):
            rel = os.path.relpath(d, root)
            dirs[:] = [x for x in dirs if os.path.join(rel, x) not in skip]
            for f in files:
                z.write(os.path.join(d, f), os.path.join(rel, f))
print(out, os.path.getsize(out))
