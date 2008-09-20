from setuptools import setup, find_packages
setup(
    name = "dj-cmdbuild",
    version = "0.2",
    packages = find_packages(exclude=['._*']),
    exclude_package_data = { '': ['*/local_*.py']},

    author = "Emanuele Pucciarelli",
    author_email = "ep@acm.org",
    description = "Tools for interfacing Django with CMDBuild databases",
    keywords = "django cmdbuild",
    url = "http://code.google.com/p/dj-cmdbuild",
    license = "GPL",

)
