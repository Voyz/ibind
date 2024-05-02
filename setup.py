from distutils.core import setup

from setuptools import find_packages

import ibind

with open("README.md", "r", encoding='utf-8') as fh:
    long_description = fh.read()

setup(
    name='ibind',
    packages=find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests", "examples", "docs", "out", "dist"]),
    version=ibind.__version__,
    license='Apache-2.0',
    description='IBind is a REST and WebSocket client library for Interactive Brokers Client Portal Web API.',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='Voy Zan',
    author_email='voy1982@yahoo.co.uk',
    url='https://github.com/Voyz/ibind',
    keywords=['interactive brokers', 'rest api', 'python api', 'ibkr python api', 'ibkr web api', 'ib api', 'ibkr api', 'algo trading', 'algorithmic trading', 'quant', 'trading'],
    install_requires=[
        'requests==2.31.*',
        'websocket-client==1.7.*'
    ],

    classifiers=[
        'Development Status :: 4 - Beta',
        # Chose either "3 - Alpha", "4 - Beta" or "5 - Production/Stable" as the current state of your package
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python :: 3.12',
    ],
)
