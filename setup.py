"""
MIT License

Copyright (c) 2016  - Edward Wells

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
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
    long_description=read('README.md'),
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
