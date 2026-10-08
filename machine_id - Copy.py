import hashlib
import uuid
import platform

def get_machine_id():
    raw = (
        platform.node() +
        platform.system() +
        platform.processor() +
        str(uuid.getnode())
    )
    return hashlib.sha256(raw.encode()).hexdigest()
print(get_machine_id())