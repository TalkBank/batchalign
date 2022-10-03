import os
from glob import glob
from setuptools import setup, find_packages

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "batchalign",
    version = "0.0.1",
    author = "TalkBank",
    author_email = "macw@cmu.edu",
    description = ("an utility to generate and align CHAT files with ASR + Forced Alignment"),
    packages=find_packages(),
    long_description=read('README.md'),
    entry_points = {
        'console_scripts': ['batchalign=baln.command_line:mainloop'],
    },
    install_requires=[
        'rev_ai'
    ],
    include_package_data=True,
    package_data={
        'baln': [os.path.basename(i) for i in glob("baln/*.cut")],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Utilities"
    ],
)


