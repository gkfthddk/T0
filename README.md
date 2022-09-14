# T0 PyPI package

This script install T0 repo and requirements with pip.
However this method can't install non-PyPI package.

Project URL: https://pypi.org/project/t0/ and https://test.pypi.org/project/t0/ (test pypi)

Based on https://github.com/dmwm/WMCore/wiki/DMWM-Packaging-with-PyPi


## Download package

    virtualenv --python=python3.6 pypienv
    source pypienv/bin/activate
    pip3 install t0=3.0.5a1

for test-pypi

    pip3 install --index-url https://test.pypi.org/simple/t0=3.0.5a1

## Upload package

To upload package pypi account and permission to pypi project are needed.

Create ~/.pypirc
```
[pypi]
repository: https://upload.pypi.org/legacy/
#manual authentication
username: yulee

[testpypi]
#repository = https://test.pypi.org/legacy/
#token authentication
username = __token__
password = pypi-...
```

### Prepare enviroment

    virtualenv --python=python3.6 pypibuild
    cd pypibuild
    source bin/activate
    pip3 install twine six docutils
    
### T0 repository
    
    git clone https://github.com/dmwm/T0.git
    cd T0
    git fetch && git fetch --tags
    git checkout <tag>

### PyPI packaging script
    git clone https://github.com/gkfthddk/T0.git T0_pypi

    cp T0_pypi/MANIFEST.in T0/
    cp T0_pypi/setup_build.py T0/
    cp T0_pypi/setup_dependencies.py T0/
    cp T0_pypi/setup_template.py T0/
    cp T0_pypi/requirements.txt T0/
    cp T0_pypi/etc/build_pypi_packages.sh T0/etc/build_pypi_packages.sh

for test-pypi    

    cp T0_pypi/etc/build_testpypi_packages.sh T0/etc/build_pypi_packages.sh

`requirments.txt` need to be checked for valid required package version.
Package will be uploaded as version in `src/python/T0/__init__.py`.
`<version>` include release version and pre, post release version(eg. `3.0.5a1`) and cannot be duplicated. Removing or replacing version is not recommanded.

### Upload package to PyPI
    cd T0
    sh etc/build_pypi_packages.sh
