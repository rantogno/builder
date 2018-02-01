#!/usr/bin/env python3
# -*- coding: utf-8 -*-

PACKAGES = {
        'libunwind': {
            'uri': 'git://git.sv.gnu.org/libunwind.git',
            },
        'libdrm': {
            'uri': 'git://anongit.freedesktop.org/drm/libdrm',
            },
        'wayland': {
            'uri': 'git://anongit.freedesktop.org/wayland/wayland',
            'autotools': '--disable-documentation'
            },
        'wayland-protocols': {
            'uri': 'git://anongit.freedesktop.org/wayland/wayland-protocols',
            },
        'mesa': {
            'uri': 'git://anongit.freedesktop.org/mesa/mesa',
            'meson': '-Dplatforms=drm,x11,wayland,surfaceless -Ddri-drivers=i965 -Dgallium-drivers= -Dvulkan-drivers=intel -Dgbm=true'
            },
        'waffle': {
            'uri': 'https://github.com/waffle-gl/waffle.git',
            },
        'piglit': {
            'uri': 'git://anongit.freedesktop.org/piglit',
            },
        'igt-gpu-tools': {
            'uri': 'git://anongit.freedesktop.org/drm/igt-gpu-tools',
            },
}

import argparse, os
import os.path
import subprocess

class Color:
    def __init__(self, msg, color):
        self.msg = msg
        self.color = color
    def __str__(self):
        return '%s%s\033[0m' % (self.color, self.msg)

class Bold(Color):
    def __init__(self, msg):
        Color.__init__(self, msg, '\033[1m')

class Blue(Color):
    def __init__(self, msg):
        Color.__init__(self, msg, '\033[34m')

class Red(Color):
    def __init__(self, msg):
        Color.__init__(self, msg, '\033[31m')

class Green(Color):
    def __init__(self, msg):
        Color.__init__(self, msg, '\033[32m')

class Yellow(Color):
    def __init__(self, msg):
        Color.__init__(self, msg, '\033[33m')

class Gray(Color):
    def __init__(self, msg):
        Color.__init__(self, msg, '\033[90m')

class Logger:
    def __init__(self, logfile, verbose=False):
        self._logfilename = logfile
        self._logfile = open(logfile, 'w')
        self._verbose = verbose
        print('logfile:', Gray(logfile))

    def log(self, msg, endl=False):
        if endl:
            msg = msg + '\n'
        self._logfile.write(msg)
        if self._verbose:
            print(msg, end='')
    def logln(self, msg):
        self.log(msg, endl=True)

class Builder:

    def __init__(self, args):
        self.__args = args

        self._setup_env()

        self.__logfile = os.path.join(self._base_dir, 'builder.log')

        self.process_options(args)
        self.logger = Logger(self.__logfile, self.__verbose)

    def process_options(self, args):
        self.__verbose = args.verbose

        if args.output is not None:
            self.__logfile = args.output

        self.__command = args.subparser
        self.process_packages(args.packages)

    def process_packages(self, packages):
        self.check_packages(packages)

        if len(packages) == 0:
            packages = PACKAGES.keys()

        self._pkgs = list(packages)

        print('packages:', Gray(str(self._pkgs)))

    def check_packages(self, packages):
        invalid = []
        for pkg in packages:
            if pkg not in PACKAGES:
                invalid.append(pkg)

        if len(invalid) > 0:
            raise Exception('Invalid packages: ' + str(invalid))

    def run(self):
        operation = {
                'install': self.install,
                'clean': self.clean,
                }

        operation[self.__command]()

    def _setup_env(self):
        env = os.environ.copy()
        basedir = os.path.abspath(os.path.curdir)

        devdir_file = os.path.join(basedir, '.builddir')

        if not os.path.exists(devdir_file):
            raise Exception("'.builddir' file doesn't exist under "
                    "current directory: '%s'" % basedir)

        if not os.path.isfile(devdir_file):
            raise Exception("%s is not a file" % devdir_file)

        self._base_dir = basedir
        self._src_dir = os.path.join(basedir, 'src')
        self._build_dir = os.path.join(basedir, 'build')
        self._inst_dir = os.path.join(basedir, 'usr')

    def _make_dirs(self):
        self.logger.logln('Creating src, build and install dirs.')
        os.makedirs(self._src_dir, exist_ok=True)
        os.makedirs(self._build_dir, exist_ok=True)
        os.makedirs(self._inst_dir, exist_ok=True)

    def install(self):
        print('Install')

        self._make_dirs()

        self.logger.logln("Starting build.")

        for p in self._pkgs:
            self._inst_pkg(p)

    def _inst_pkg(self, pkg):
        self.logger.logln('')
        self.logger.logln('Installing package: ' + pkg)

        srcdir = os.path.join(self._src_dir, pkg)
        builddir = os.path.join(self._build_dir, pkg)

        self._fetch_pkg(pkg, srcdir)
        self._build_pkg(pkg, srcdir, builddir)

    def _fetch_pkg(self, pkg, srcdir):
        print('Fetching %s: ' % pkg, end='', flush=True)

        if os.path.exists(srcdir) and os.path.isdir(srcdir):
            print(Gray('SKIP'))
            return
        cmd = ['git', 'clone', PACKAGES[pkg]['uri'], srcdir]
        self._call(cmd)
        print(Green('DONE'))

    def _build_pkg(self, pkg, srcdir, builddir):
        print('Building %s: ' % pkg, end='')

        builtfile = os.path.exists(os.path.join(builddir, '.builder'))

        if os.path.exists(builddir) and os.path.isdir(builddir):
            if os.path.exists(builtfile) and os.path.isdir(builtfile):
                print(Gray('SKIP'))
                return

        if os.path.exists(os.path.join(srcdir, 'meson.build')):
            self._build_meson(pkg, srcdir, builddir)
        elif os.path.exists(os.path.join(srcdir, 'autogen.sh')):
            self._build_autotools(pkg, srcdir, builddir)
        elif os.path.exists(os.path.join(srcdir, 'CMakeLists.txt')):
            self._build_cmake(pkg, srcdir, builddir)

        print(Green('DONE'))

    def _build_meson(self, pkg, srcdir, builddir):
        self.logger.logln('Building %s with meson.' % pkg)

    def _build_autotools(self, pkg, srcdir, builddir):
        self.logger.logln('Building %s with autotools.' % pkg)

    def _build_cmake(self, pkg, srcdir, builddir):
        self.logger.logln('Building %s with cmake.' % pkg)

    def clean(self):
        print('Clean')
        self.logger.logln("Starting cleaning.")

        for p in self._pkgs:
            self._clean_pkg(p)

    def _clean_pkg(self, pkg):
        self.logger.logln('Cleaning package: ' + pkg)

    def _call(self, cmd):
        if type(cmd) != type([]) or len(cmd) == 0:
            raise Exception('Invalid command to _call', cmd)

        self.logger.logln(' '.join(cmd))
        cmd = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, universal_newlines=True)
        result = cmd.wait()
        output = cmd.stdout.read()
        self.logger.log(output)

        if result != 0:
            raise Exception('Command failed', cmd, result)

def main():
    parser = argparse.ArgumentParser(description='Builder for mesa')
    parser.add_argument('--verbose', '-v', action='store_true')
    parser.add_argument('--output', '-o', help='log file')

    pkg_parser = argparse.ArgumentParser(add_help=False)
    pkg_parser.add_argument('packages', metavar='PKG', type=str, nargs='*',
            help='package to process')

    commands = parser.add_subparsers(help='commands to run', dest='subparser')

    # Install packages
    install_p = commands.add_parser('install',
            parents=[pkg_parser],
            help='build and install packages')

    # Clean packages
    clean_p = commands.add_parser('clean',
            parents=[pkg_parser],
            help='clean package source dir')

    args = parser.parse_args()

    if args.subparser is not None:
        builder = Builder(args)
        builder.run()
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
