#!/usr/bin/env python3
import json
import shutil

print(
    json.dumps(
        {name: bool(shutil.which(name)) for name in ("libreoffice", "pdftoppm", "tesseract")},
        sort_keys=True,
    )
)
