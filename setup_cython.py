from Cython.Build import cythonize
from setuptools import Extension, setup


extension = Extension(
    name="cython_matcher",
    sources=["cython_matcher.pyx"],
)

setup(
    name="chronosmatch-cython-core",
    ext_modules=cythonize(
        [extension],
        compiler_directives={
            "language_level": 3,
            "boundscheck": False,
            "wraparound": False,
            "initializedcheck": False,
        },
        build_dir="build/cython",
    ),
)
