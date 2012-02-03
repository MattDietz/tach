import os
from setuptools import setup, find_packages
from setuptools.command.sdist import sdist


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name='tach',
    version='0.1',
    author='Matthew Dietz',
    author_email='matthew.dietz@gmail.com',
    description=(""),
    license='Apache License (2.0)',
    keywords='metrics',
    packages=find_packages(exclude=['tests']),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2.6'
    ],
    url='https://github.com/Cerberus98/tach',
    scripts=['bin/tach'],
    long_description=read('README.md'),
    install_requires=[''],
    data_files=[('', ['etc/tach.conf.example'])],
    zip_safe=False
)
