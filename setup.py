from setuptools import setup, find_packages

setup(
    name="django-wflow",
    #url="http://github.com/aaboffill/django-wflow/",
    author="Adonys Alea Boffill",
    author_email="aaboffill@gmail.com",
    version="0.1.7",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    description="A workflow solution for django applications, based on django-workflows core.",
    install_requires=['Django>=1.6.1', 'django-permissions==1.0.3', 'South==0.8.4'],
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.3",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries",
        "Topic :: Utilities",
        "Environment :: Web Environment",
        "Framework :: Django",
    ],

)
