import os

dependencies = [
    "requests",
    "pandas",
    "openpyxl",
    "pyinstaller",  # Include any other necessary dependencies here
]

for dependency in dependencies:
    os.system(f"pip install {dependency}")
