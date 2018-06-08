# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
import io
import os


about = {}
about_filename = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'finctrl', '__about__.py')
with io.open(about_filename, 'rb') as fp:
    exec(fp.read(), about)


setup(
    name='finctrl',
    version=about['__version__'],
    description='finctrl',
    author='Alexander Pyatkin',
    author_email='aspyatkin@gmail.com',
    url='https://github.com/aspyatkin/finctrl',
    license='MIT',
    packages=find_packages('.'),
    install_requires=[
        'peewee==2.10.1',
        'Cython>=0.26',
        'click==6.7'
    ],
    entry_points={
        'console_scripts': [
            'finctrl = finctrl:cli',
        ]
    }
)
