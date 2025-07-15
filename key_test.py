import os
from cryptography.fernet import Fernet

key = os.environ.get("GITHUB_TOKEN_ENCRYPTION_KEY")
print("Loaded key:", key)
fernet = Fernet(key)  # Should NOT raise
print("Key is valid.")
