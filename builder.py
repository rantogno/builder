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

def check_packages(packages):
    invalid = False
    for pkg in packages:
        if pkg not in PACKAGES:
            print('invalid pkg name:', pkg)
            invalid = True;

    return not invalid

def process_pkgs(args):
    if not check_packages(args.packages):
        return False

    if not process_options(args):
        return False

    for pkg in args.packages:
        if pkg in PACKAGES:
            args.func(pkg)

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
        self.__logfile = '/tmp/builder.log'

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

    def install(self):
        print('Install')
        self.logger.logln("Starting build.")

        for p in self._pkgs:
            self._inst_pkg(p)

    def _inst_pkg(self, pkg):
        self.logger.logln('Installing package: ' + pkg)

    def clean(self):
        print('Clean')
        self.logger.logln("Starting cleaning.")

        for p in self._pkgs:
            self._clean_pkg(p)

    def _clean_pkg(self, pkg):
        self.logger.logln('Cleaning package: ' + pkg)

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
