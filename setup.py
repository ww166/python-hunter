#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import io
import os
import re
import sys
from distutils.command.build import build
from glob import glob
from itertools import chain
from os.path import basename
from os.path import dirname
from os.path import join
from os.path import relpath
from os.path import splitext

from setuptools import Extension
from setuptools import find_packages
from setuptools import setup
from setuptools.command.build_ext import build_ext
from setuptools.command.develop import develop
from setuptools.command.easy_install import easy_install
from setuptools.command.install_lib import install_lib
from setuptools.dist import Distribution

try:
    # Allow installing package without any Cython available. This
    # assumes you are going to include the .c files in your sdist.
    import Cython
except ImportError:
    Cython = None


def read(*names, **kwargs):
    with io.open(
        join(dirname(__file__), *names),
        encoding=kwargs.get('encoding', 'utf8'),
    ) as fh:
        return fh.read()


class BuildWithPTH(build):
    def run(self):
        super().run()
        path = join(dirname(__file__), 'src', 'hunter.pth')
        dest = join(self.build_lib, basename(path))
        self.copy_file(path, dest)


class EasyInstallWithPTH(easy_install):
    def run(self, *args, **kwargs):
        super().run(*args, **kwargs)
        path = join(dirname(__file__), 'src', 'hunter.pth')
        dest = join(self.install_dir, basename(path))
        self.copy_file(path, dest)


class InstallLibWithPTH(install_lib):
    def run(self):
        super().run()
        path = join(dirname(__file__), 'src', 'hunter.pth')
        dest = join(self.install_dir, basename(path))
        self.copy_file(path, dest)
        self.outputs = [dest]

    def get_outputs(self):
        return chain(install_lib.get_outputs(self), self.outputs)


class DevelopWithPTH(develop):
    def run(self):
        super().run()
        path = join(dirname(__file__), 'src', 'hunter.pth')
        dest = join(self.install_dir, basename(path))
        self.copy_file(path, dest)


class OptionalBuildExt(build_ext):
    """Allow the building of C extensions to fail."""

    def run(self):
        try:
            if os.environ.get('SETUPPY_FORCE_PURE'):
                raise Exception('C extensions disabled (SETUPPY_FORCE_PURE)!')
            super().run()
        except Exception as e:
            self._unavailable(e)
            self.extensions = []  # avoid copying missing files (it would fail).

    def _unavailable(self, e):
        print('*' * 80)
        print(
            """WARNING:

    An optional code optimization (C extension) could not be compiled.

    Optimizations for this package will not be available!
        """
        )

        print('CAUSE:')
        print('')
        print('    ' + repr(e))
        print('*' * 80)


class BinaryDistribution(Distribution):
    """Distribution which almost always forces a binary package with platform name"""

    def has_ext_modules(self):
        return super().has_ext_modules() or not os.environ.get('SETUPPY_ALLOW_PURE')


setup(
    name='hunter',
    use_scm_version={
        'local_scheme': 'dirty-tag',
        'write_to': 'src/hunter/_version.py',
        'fallback_version': '3.5.1',
    },
    license='BSD-2-Clause',
    description='Hunter is a flexible code tracing toolkit.',
    long_description='%s\n%s'
    % (
        re.compile('^.. start-badges.*^.. end-badges', re.M | re.S).sub('', read('README.rst')),
        re.sub(':[a-z]+:`~?(.*?)`', r'``\1``', read('CHANGELOG.rst')),
    ),
    author='Ionel Cristian Mărieș',
    author_email='contact@ionelmc.ro',
    url='https://github.com/ionelmc/python-hunter',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    py_modules=[splitext(basename(path))[0] for path in glob('src/*.py')],
    zip_safe=False,
    classifiers=[
        # complete classifier list: http://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: Unix',
        'Operating System :: POSIX',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Utilities',
        'Topic :: Software Development :: Debuggers',
    ],
    project_urls={
        'Documentation': 'https://python-hunter.readthedocs.io/',
        'Changelog': 'https://python-hunter.readthedocs.io/en/latest/changelog.html',
        'Issue Tracker': 'https://github.com/ionelmc/python-hunter/issues',
    },
    keywords=[
        'trace',
        'tracer',
        'settrace',
        'debugger',
        'debugging',
        'code',
        'source',
    ],
    python_requires='>=3.7',
    install_requires=[],
    extras_require={
        ':platform_system != "Windows"': ['manhole >= 1.5'],
    },
    setup_requires=[
        'setuptools_scm>=3.3.1,!=4.0.0',
        'cython',
    ]
    if Cython
    else [
        'setuptools_scm>=3.3.1,!=4.0.0',
    ],
    entry_points={
        'console_scripts': [
            'hunter-trace = hunter.remote:main',
        ]
    },
    cmdclass={
        'build': BuildWithPTH,
        'easy_install': EasyInstallWithPTH,
        'install_lib': InstallLibWithPTH,
        'develop': DevelopWithPTH,
        'build_ext': OptionalBuildExt,
    },
    ext_modules=[]
    if hasattr(sys, 'pypy_version_info')
    else [
        Extension(
            splitext(relpath(path, 'src').replace(os.sep, '.'))[0],
            sources=[path],
            extra_compile_args=os.environ.get('SETUPPY_CFLAGS', '').split(),
            include_dirs=[dirname(path)],
        )
        for root, _, _ in os.walk('src')
        for path in glob(join(root, '*.pyx' if Cython else '*.c'))
    ],
    distclass=BinaryDistribution,
)
