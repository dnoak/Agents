from dataclasses import dataclass
from glob import glob
import json
import os
from pathlib import Path
import timeit
import requests

@dataclass
class Timer:
    @staticmethod
    def timer(func):
        def wrapper(*args, **kwargs):
            start = timeit.default_timer()
            result = func(*args, **kwargs)
            end = timeit.default_timer()
            return result, end - start
        return wrapper

@dataclass
class FileDownloader:
    download_folder: str
    def download(self, url: str, audio_filename: str) -> str:
        if not os.path.exists(self.download_folder):
            os.makedirs(self.download_folder)
        download_path = Path(self.download_folder) / audio_filename
        response = requests.get(url)
        response.raise_for_status()
        with open(download_path, 'wb') as file:
            file.write(response.content)
        return download_path.resolve().as_posix()

