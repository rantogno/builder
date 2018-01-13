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

import argparse

def pkg_install(args):
    print("installing packages: ", args)

def pkg_clean(args):
    pass

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

    for pkg in args.packages:
        if pkg in PACKAGES:
            print('pkg:', pkg)

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
    install_p.set_defaults(func=pkg_install)

    # Clean packages
    clean_p = commands.add_parser('clean',
            parents=[pkg_parser],
            help='clean package source dir')
    clean_p.set_defaults(func=pkg_clean)

    args = parser.parse_args()

    if args.subparser is not None:
        process_pkgs(args)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
