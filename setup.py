from setuptools import find_packages, setup

setup(
    name="ai_personal_trainer",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "requests",
        "python-dotenv",
        "couchdb",
        "cryptography",
    ],
)
