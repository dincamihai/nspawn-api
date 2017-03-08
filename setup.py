from setuptools import setup

setup(
    name='nspawn-api',
    packages=['nspawn'],
    include_package_data=True,
    install_requires=[
        'gunicorn',
        'nsenter',
        'flask',
        'pydbus',
        'supervisor'
    ],
)
