import platform
import struct


def benchmark_environment():
    return {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "operating_system": platform.system(),
        "os_release": platform.release(),
        "machine": platform.machine(),
        "pointer_bits": struct.calcsize("P") * 8,
    }