from setuptools import setup, find_packages

setup(
    name="party-games",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "python-socketio",
        "sqlalchemy",
        "qrcode",
        "jinja2",
        "python-multipart",
        "pillow",
        "requests",
        "netifaces",
    ],
)