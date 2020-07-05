from setuptools import setup, find_packages

setup(name='photomanip',
      version='0.2.1',
      description='average like, all the photos',
      author='Andrew Catellier',
      author_email='andrew@thisisreal.net',
      packages=find_packages(),
      include_package_data=True,
      package_data={'': ['*.jpg']}
)
