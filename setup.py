import os

from setuptools import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="fbparser",
    version="1.0.0",
    author="Edward Wells",
    author_email="git@edward.sh",
    description=("Library/CLI utility to parse, organize and "
                 "export messages in Facebook archives"),
    long_description=read('README.rst'),
    keywords="facebook fb message messages archive parser parsing export",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.5"
    ],
    license="MIT",
    url="https://github.com/arcward/fbparser",
    packages=['fbparser'],
    install_requires=['python-dateutil>=2.5.3'],
    entry_points = {
        'console_scripts': ['fbparser=fbparser.fbparser:command_line']
    }
)
