from setuptools import setup

setup(
    name='TVShowFetch',
    version='1.0.0',
    description='Fetches TV shows from network websites',
    author='Jacob Truman',
    author_email='jacob.truman@gmail.com',
    url='https://github.com/jacobtruman/TVShowFetch',
    packages=['tv_show_fetch', 'fetchers'],
    scripts=['bin/TVShowFetchRunner.py'],
    install_requires=['requests>=2.11.0', 'beautifulsoup4', 'youtube_dl', 'pycrypto', 'TruLogger'],
    dependency_links=['git+git://github.com/jacobtruman/TruLogger.git#egg=TruLogger-1.0.0']
)
