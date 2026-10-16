from setuptools import setup, find_packages

# frappe and erpnext are bench-managed; do NOT list them as pip dependencies.
# Declaring them here causes uv to try to resolve frappe's own git-URL sub-deps
# (e.g. pypika @ git+...) which fails. Runtime app dependency is declared via
# required_apps in hooks.py instead.

setup(
    name="baby_care",
    version="1.0.0",
    description="Baby Care Management — Nursery, Daycare & Childcare for ERPNext v15/v16",
    author="Baby Care",
    author_email="admin@babycare.example",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=[],
)
