#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse

def pkg_install(args):
    print("installing packages: ", args)

def pkg_clean(args):
    pass

def main():
    parser = argparse.ArgumentParser(description='Builder for mesa')
    parser.add_argument('--verbose', '-v', action='store_true')
    parser.add_argument('--output', '-o', help='log file')

    pkg_parser = argparse.ArgumentParser(add_help=False)
    pkg_parser.add_argument('packages', metavar='PKG', type=str, nargs='*',
            help='package to process')

    commands = parser.add_subparsers(help='commands to run')

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
    args.func(args)

if __name__ == '__main__':
    main()
