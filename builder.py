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


class Logger:
    def __init__(self, logfile):
        print('logfile:', logfile)

class Builder:

    def __init__(self, args):
        self.__args = args
        self.__logfile = '/tmp/builder.log'

        self.process_options(args)
        self.logger = Logger(self.__logfile)

    def process_options(self, args):
        self.__verbose = args.verbose

        if args.output is not None:
            self.__logfile = args.output

        self.__command = args.subparser

    def run(self):
        operation = {
                'install': self.install,
                'clean': self.clean,
                }

        operation[self.__command]()

    def install(self):
        print("Install")

    def clean(self):
        print('Clean')

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
