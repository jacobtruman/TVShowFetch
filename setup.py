from setuptools import setup


setup(
    name='TVShowFetch',
    version='1.0.0',
    description='Fetches TV shows from network websites',
    author='Jacob Truman',
    author_email='jacob.truman@gmail.com',
    url='',
    packages=['tv_show_fetch'],
    scripts=['bin/TVShowFetchRunner.py'],
    install_requires=['requests', 'beautifulsoup4', 'youtube_dl', 'pycrypto'],
    dependency_links=[]
)