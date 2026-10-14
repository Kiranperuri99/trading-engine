import mmap


class MappedStorage:
    def __init__(self, path, size):
        if type(size) is not int or size <= 0:
            raise ValueError("Size must be a positive whole number")

        # "x+b" creates a new file and refuses to overwrite existing files.
        self._file = open(path, "x+b")

        try:
            self._file.truncate(size)
            self.buffer = mmap.mmap(self._file.fileno(), size)
        except Exception:
            self._file.close()
            raise

    def close(self):
        self.buffer.close()
        self._file.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()