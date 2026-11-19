
import os
import platform
import re

def log(text):
    print(text, flush=1)

mupdf_version = '1.28.6'
mupdf_version_tuple = (1, 28, 6)

def devel(make_links=True):
    '''
    Allows PyMuPDF installation to be used to compile and link programmes that
    use the MuPDF C/C++ API.

    Args:
        make_links:
            If true, then on non-windows we also create softlinks to any shared
            libraries that are supplied with a version suffix; this allows them
            to be used in a link command.

            For example we create links such as:

            site-packages/pymupdf/
                libmupdf.so -> libmupdf.so.26.7
                libmupdfcpp.so -> libmupdfcpp.so.26.7

    Returns: (mupdf_include, mupdf_lib).
        mupdf_include:
            Path of MuPDF include directory within PyMuPDF install.
        mupdf_lib
            Path of MuPDF library directory within PyMuPDF install.
    '''
    import platform

    log(f'{mupdf_version=}')

    p = os.path.normpath(f'{__file__}/..')

    mupdf_include = f'{p}/mupdf-devel/include'

    if platform.system() == 'Windows':
        # Separate .lib files are used at build time.
        mupdf_lib = f'{p}/mupdf-devel/lib'
    else:
        # .so files are used for both buildtime and runtime linking.
        mupdf_lib = p
    log(f'Within installed PyMuPDF:')
    log(f'    {mupdf_include=}')
    log(f'    {mupdf_lib=}')

    assert os.path.isdir(mupdf_include), f'Not a directory: {mupdf_include=}.'
    assert os.path.isdir(mupdf_lib), f'Not a directory: {mupdf_lib=}.'

    if platform.system() != 'Windows' and make_links:
        # Make symbolic links within the installed pymupdf module so
        # that ld can find libmupdf.so etc. This is a bit of a hack, but
        # necessary because wheels cannot contain symbolic links.
        #
        # For example we create `libmupdf.so -> libmupdf.so.24.8`.
        #
        # We are careful to only create symlinks for the expected MuPDF
        # version, in case old .so files from a previous install are still
        # in place.
        #
        log(f'Creating symlinks in {mupdf_lib=} for MuPDF-{mupdf_version} .so files.')
        regex_suffix = mupdf_version.split('.')[1:3]
        regex_suffix = '[.]'.join(regex_suffix)
        mupdf_lib_regex = f'^(lib[^.]+[.]so)[.]{regex_suffix}$'
        log(f'{mupdf_lib_regex=}.')
        for leaf in os.listdir(mupdf_lib):
            m = re.match(mupdf_lib_regex, leaf)
            if m:
                pfrom = f'{mupdf_lib}/{m.group(1)}'
                # os.path.exists() can return false if softlink exists
                # but points to non-existent file, so we also use
                # `os.path.islink()`.
                if os.path.islink(pfrom) or os.path.exists(pfrom):
                    log(f'Removing existing link {pfrom=}.')
                    os.remove(pfrom)
                log(f'Creating symlink: {pfrom} -> {leaf}')
                os.symlink(leaf, pfrom)

    return mupdf_include, mupdf_lib
