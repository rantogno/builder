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
            'skipinstall': True,
            },
        'igt-gpu-tools': {
            'uri': 'git://anongit.freedesktop.org/drm/igt-gpu-tools',
            },
}

import argparse, os
import os.path
import subprocess
import json

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
        self._logfile = open(logfile, 'w', buffering=1)
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

    def get_file(self):
        return self._logfile

class Pkg:
    def __init__(self, name, basedir, logger, env):
        self.name = name
        self._logger = logger
        self._env = env

        confdir = os.path.join(basedir, '.workdir')
        self.jsonpath = os.path.join(confdir, name + '.json')
        if os.path.exists(self.jsonpath):
            self._load_from(self.jsonpath)
        else:
            self._create_new(basedir)

        self._inst_dir = os.path.join(basedir, 'usr')

    def _create_new(self, basedir):
        self._logger.logln('Creating new config for: %s' % self.name)

        srcdir = os.path.join(basedir, 'src')
        builddir = os.path.join(basedir, 'build')
        workdir = os.path.join(basedir, '.workdir')

        self.srcpath = os.path.join(srcdir, self.name)
        self.buildpath = os.path.join(builddir, self.name)

        pkgconf = PACKAGES[self.name]

        self._skipinstall = pkgconf.get('skipinstall', False)

        self._config = {
            'meson': pkgconf.get('meson'),
            'autotools': pkgconf.get('autotools'),
            'cmake': pkgconf.get('cmake'),
        }

        self._configured = False
        self._built = False

        self.update()

    def _load_from(self, jsonpath):
        jsonfile = open(jsonpath)
        pkg = json.load(jsonfile)

        self._logger.logln('Loading config for: %s' % self.name)
        self._logger.logln(str(pkg))

        if not '__builder__' in pkg:
            raise Exception('%s is not a "Pkg" config file' % jsonpath)

        self.srcpath = pkg['srcpath']
        self.buildpath = pkg['buildpath']
        self._config = pkg['config']
        self._configured = pkg['state']['configured']
        self._built = pkg['state']['built']
        self._skipinstall = pkg['skipinstall']

    def get_conf(self, conftype):
        return self._config.get(conftype)

    def _to_json(self):
        json_dict = {
            '__builder__': True,
            'name': self.name,
            'srcpath': self.srcpath,
            'buildpath': self.buildpath,
            'config': self._config,
            'state': {
                'configured': self._configured,
                'built': self._built,
            },
            'skipinstall': self._skipinstall,
        }

        return json_dict

    def update(self):
        jsonfile = open(self.jsonpath, 'w')
        json.dump(self, jsonfile, indent=4, default=Pkg._to_json)
        jsonfile.close()

    def __str__(self):
        return self.name

    def _call(self, cmd, cwd=None, env=None):
        if env is None:
            env = self._env

        if type(cmd) != type([]) or len(cmd) == 0:
            raise Exception('Invalid command to _call', cmd)

        self._logger.logln(' '.join(cmd))
        cmdprocess = subprocess.Popen(cmd, stdout=self._logger.get_file(),
                stderr=subprocess.STDOUT, universal_newlines=True,
                cwd=cwd, env=env)
        result = cmdprocess.wait()

        if result != 0:
            raise Exception('Command failed', cmd, result)

    def _fetch(self):
        print('Fetching %s: ' % self.name, end='', flush=True)

        if os.path.exists(self.srcpath) and os.path.isdir(self.srcpath):
            print(Gray('SKIP'))
            return
        cmd = ['git', 'clone', PACKAGES[pkgname]['uri'], self.srcpath]
        self._call(cmd)
        print(Green('DONE'))

    def _build(self):
        if self._skipinstall:
            self._logger.logln('Skipping install of "%s"' % self.name)
            return

        print('Building %s: ' % self.name, end='')

        if self._built:
            print(Gray('SKIP'))
            return

        if os.path.exists(os.path.join(self.srcpath, 'meson.build')):
            self._build_meson()
        elif os.path.exists(os.path.join(self.srcpath, 'autogen.sh')):
            self._build_autotools()
        elif os.path.exists(os.path.join(self.srcpath, 'CMakeLists.txt')):
            self._build_cmake()

        self._built = True
        self.update()

        print(Green('DONE'))

    def _build_meson(self):
        self._logger.logln('Building %s with meson.' % self.name)

        self._call_meson()
        self._call_ninja()

    def _build_autotools(self):
        self._logger.logln('Building %s with autotools.' % self.name)

        self._call_configure()
        self._call_make()

    def _build_cmake(self):
        self._logger.logln('Building %s with cmake.' % self.name)

        self._call_cmake()
        self._call_ninja()

    def _call_meson(self):
        mesonopts = self.get_conf('meson')
        self._logger.logln('Build opts: "%s"' % mesonopts)

        cmd = ['meson']
        cmd.append('--prefix=%s' % self._inst_dir)
        if mesonopts:
            cmd.extend(mesonopts.split())
        cmd.append(self.buildpath)

        self._call(cmd, self.srcpath)

        self._configured = True
        self.update()

    def _call_ninja(self):
        cmd = ['ninja']
        self._call(cmd, self.buildpath)

        cmd.append('install')
        self._call(cmd, self.buildpath)

    def _call_configure(self):
        autoopts = self.get_conf('autotools')
        self._logger.logln('Build opts: "%s"' % autoopts)

        cmd = ['./autogen.sh']
        self._call(cmd, self.srcpath)

        os.makedirs(self.buildpath, exist_ok=True)
        cmd = ['%s/configure' % self.srcpath]
        cmd.append('--prefix=%s' % self._inst_dir)
        if autoopts:
            cmd.extend(autoopts.split())
        self._call(cmd, self.buildpath)

        self._configured = True
        self.update()

    def _call_make(self):
        cmd = ['make']
        cmd.append('-j%d' % os.cpu_count())
        self._call(cmd, self.buildpath)

        cmd.append('install')
        self._call(cmd, self.buildpath)

    def _call_cmake(self):
        cmakeopts = self.get_conf('cmake')
        self._logger.logln('Build opts: "%s"' % cmakeopts)

        os.makedirs(self.buildpath, exist_ok=True)
        cmd = ['cmake']
        cmd.append(self.srcpath)
        cmd.append('-DCMAKE_INSTALL_PREFIX=%s' % self._inst_dir)
        cmd.append('-GNinja')
        if cmakeopts:
            cmd.extend(cmakeopts.split())

        self._call(cmd, self.buildpath)

        self._configured = True
        self.update()

    def install(self):
        self._logger.logln('')
        self._logger.logln('Installing package: ' + self.name)

        self._fetch()
        self._build()

    def clean(self):
        self._logger.logln('')
        self._logger.logln('Cleaning package: ' + self.name)
        cmd = ['git', 'clean', '-fdx']
        self._call(cmd, self.srcpath)

class Builder:

    def __init__(self, args):
        self.__args = args

        self._setup_env()

        self.__logfile = os.path.join(self._base_dir, 'builder.log')

        self.process_options(args)
        self.logger = Logger(self.__logfile, self.__verbose)

        os.makedirs(self._work_dir, exist_ok=True)

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
        basedir = os.path.abspath(os.path.curdir)

        devdir_file = os.path.join(basedir, '.builddir')

        if not os.path.exists(devdir_file):
            raise Exception("'.builddir' file doesn't exist under "
                    "current directory: '%s'" % basedir)

        if not os.path.isfile(devdir_file):
            raise Exception("%s is not a file" % devdir_file)

        self._base_dir = basedir
        self._work_dir = os.path.join(basedir, 'src')
        self._src_dir = os.path.join(basedir, 'src')
        self._build_dir = os.path.join(basedir, 'build')
        self._inst_dir = os.path.join(basedir, 'usr')

        self._setup_envvars()

    def _setup_envvars(self):
        env = os.environ.copy()
        usr = self._inst_dir

        libdir = os.path.join(usr, 'lib')
        lib64dir = os.path.join(usr, 'lib64')
        env['LD_LIBRARY_PATH'] = ':'.join((libdir, lib64dir))

        pkglib = os.path.join(libdir, 'pkgconfig')
        pkg64lib = os.path.join(lib64dir, 'pkgconfig')
        pkgshare = os.path.join(usr, 'share/pkgconfig')
        env['PKG_CONFIG_PATH'] = ':'.join((pkglib, pkg64lib, pkgshare))

        path = os.path.join(usr, 'bin')
        env['PATH'] = ':'.join((path, env['PATH']))

        aclocalpath = os.path.join(usr, 'share/local')
        env['ACLOCAL_PATH'] = aclocalpath
        env['ACLOCAL'] = 'aclocal -I ' + aclocalpath

        env['CMAKE_PREFIX_PATH'] = usr
        env['NOCONFIGURE'] = '1'

        self._env = env

    def _make_dirs(self):
        self.logger.logln('Creating src, build and install dirs.')
        os.makedirs(self._src_dir, exist_ok=True)
        os.makedirs(self._build_dir, exist_ok=True)
        os.makedirs(self._inst_dir, exist_ok=True)
        os.makedirs(self._env['ACLOCAL_PATH'], exist_ok=True)

    def _process_pkg(self, pkgname, operation):
        self.logger.logln('')

        pkg = Pkg(pkgname, self._base_dir, self.logger, self._env)

        operation(pkg)

    def install(self):
        print('Install')

        self._make_dirs()

        self.logger.logln("Starting build.")

        for p in self._pkgs:
            self._process_pkg(p, self._inst_pkg)

    def _inst_pkg(self, pkg):
        pkg.install()
        return

    def clean(self):
        print('Clean')

        self.logger.logln("Starting cleaning.")

        for p in self._pkgs:
            self._process_pkg(p, self._clean_pkg)

    def _clean_pkg(self, pkg):
        self.logger.logln('Cleaning package: ' + pkg['name'])
        pkg.clean()

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
