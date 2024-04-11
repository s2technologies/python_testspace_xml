from setuptools import setup, find_packages

setup(
    name='python_testspace_xml',
    version='1.2',
    packages=find_packages(include=['python_testspace_xml', 'python_testspace_xml.*']),
    url='',
    license="MIT license",
    author="Ivailo Petrov",
    author_email='ivailop@s2technologies.com',
    description="Module for generating Testspace XML format result files",
)
