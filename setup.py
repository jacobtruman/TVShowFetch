from setuptools import setup


setup(
    name='TVShowFetch',
    version='0.0.1',
    description='Fetches TV shows from network websites',
    author='Jacob Truman',
    author_email='jacob.truman@gmail.com',
    url='',
    packages=['TVShowFetch'],
    scripts=[],
    install_requires=['requests', 'beautifulsoup4', 'youtube_dl'],
    dependency_links=[]
)