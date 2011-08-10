#!/usr/bin/env python
# -*- coding: utf-8 -*-

from distutils.core import setup


setup(
    name="django-resubmit",
    version="0.5",
    license = 'BSD',
    description="Resubmitable file widgets for Django",
    packages=['django_resubmit'],
    package_data={'django_resubmit': ['static/django_resubmit/*']},
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
    ]
)
