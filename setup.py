from setuptools import setup, find_packages

setup(
    name='python_testspace_xml',
    version='',
    packages=find_packages(include=['python_testspace_xml', 'python_testspace_xml.*']),
    url='',
    license="MIT license",
    author="Jeffrey Schultz",
    author_email='jeffs@s2technologies.com',
    description="Module for interacting with Testspace Server",
    install_requires=[
        'lxml',
        'six'
    ]
)
