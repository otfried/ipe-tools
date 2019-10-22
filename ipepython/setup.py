from distutils.core import setup, Extension

# compile options to find Lua and Ipe headers and libraries
lua_includes = [ '-I/usr/include/lua5.3' ]
lua_libs = [ '-llua5.3' ]

ipe_srcdir = '../../ipe/src'
ipe_libdir = '../../ipe/build/lib'

ipe_includes = [ '-I%s/include' % ipe_srcdir ]
ipe_libs = [ '-L%s' % ipe_libdir, '-lipelua', '-lipe' ]

ipemodule = Extension('ipe',
                      sources = ['ipepython.cpp'],
                      extra_compile_args = lua_includes + ipe_includes,
                      extra_link_args = lua_libs + ipe_libs,
)

setup(name = 'ipe',
      version = '2019.09.10',
      description = 'Use Ipelib from Python',
      url = 'https://github.com/otfried/ipe-tools/tree/python3/ipepython',
      author = 'Otfried Cheong',
      author_email = 'ipe@otfried.org',
      license = 'GPL3',
      ext_modules = [ipemodule],
)
