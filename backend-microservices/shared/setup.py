"""
Shared package for ParkSmart microservices.

Install in each service with:
    pip install -e /app/shared/

Or in Dockerfile:
    COPY shared/ /app/shared/
    RUN pip install -e /app/shared/
"""
from setuptools import setup, find_packages

setup(
    name='parksmart-shared',
    version='1.0.0',
    description='Shared utilities for ParkSmart microservices',
    packages=['shared'],
    package_dir={'shared': '.'},
    py_modules=[
        'gateway_permissions',
        'gateway_middleware',
    ],
    install_requires=[
        'djangorestframework>=3.14.0',
    ],
    python_requires='>=3.10',
)
