from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

setup(
    name="baby_care",
    version="1.0.0",
    description="Baby Care Management — Nursery, Daycare & Childcare for ERPNext v15/v16",
    author="Baby Care",
    author_email="admin@babycare.example",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)
