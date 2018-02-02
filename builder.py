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
        basedir = os.path.abspath(os.path.curdir)

        devdir_file = os.path.join(basedir, '.builddir')

        if not os.path.exists(devdir_file):
            raise Exception("'.builddir' file doesn't exist under "
                    "current directory: '%s'" % basedir)

        if not os.path.isfile(devdir_file):
            raise Exception("%s is not a file" % devdir_file)

        self._base_dir = basedir
        self._conf_dir = os.path.join(basedir, '.workdir')
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
        os.makedirs(self._conf_dir, exist_ok=True)
        os.makedirs(self._src_dir, exist_ok=True)
        os.makedirs(self._build_dir, exist_ok=True)
        os.makedirs(self._inst_dir, exist_ok=True)
        os.makedirs(self._env['ACLOCAL_PATH'], exist_ok=True)

    def _create_pkg_conf(self, pkgname):
            pkg = {}
            pkg['name'] = pkgname
            pkg['conf'] = os.path.join(self._conf_dir, pkgname + '.json')
            pkg['src'] = os.path.join(self._src_dir, pkgname)
            pkg['build'] = os.path.join(self._build_dir, pkgname)

            pkgconf = PACKAGES[pkgname]
            skipinstall = pkgconf.get('skipinstall', False)
            pkg['config'] = {
                    'skipinstall': pkgconf.get('skipinstall', False),
                    'meson': pkgconf.get('meson'),
                    'autotools': pkgconf.get('autotools'),
                    'cmake': pkgconf.get('cmake'),
                }

            pkg['state'] = {
                    'configured': False,
                    'built': False,
                    'installed': False,
                }

            return pkg

    def _process_pkg(self, pkgname, operation):
        self.logger.logln('')
        conf = os.path.join(self._conf_dir, pkgname + '.json')

        if os.path.exists(conf):
            conffile = open(conf)
            pkg = json.load(conffile)
            self.logger.logln('Loading config for: %s' % pkgname)
            self.logger.logln(str(pkg))
        else:
            pkg = self._create_pkg_conf(pkgname)
            self.logger.logln('Creating new config for: %s' % pkgname)
            conffile = open(conf, 'w')
            json.dump(pkg, conffile, indent=4)

        operation(pkg)

    def install(self):
        print('Install')

        self._make_dirs()

        self.logger.logln("Starting build.")

        for p in self._pkgs:
            self._process_pkg(p, self._inst_pkg)

    def _inst_pkg(self, pkg):
        self.logger.logln('')
        self.logger.logln('Installing package: ' + pkg['name'])

        self._fetch_pkg(pkg)
        self._build_pkg(pkg)

    def _fetch_pkg(self, pkg):
        pkgname = pkg['name']
        print('Fetching %s: ' % pkgname, end='', flush=True)

        if os.path.exists(pkg['src']) and os.path.isdir(pkg['src']):
            print(Gray('SKIP'))
            return
        cmd = ['git', 'clone', PACKAGES[pkgname]['uri'], pkg['src']]
        self._call(cmd)
        print(Green('DONE'))

    def _update_json(self, pkg):
        json.dump(pkg, pkg['conf'], indent=4)

    def _build_pkg(self, pkg):

        if pkg['config'].get('skipinstall'):
            self.logger.logln('Skipping install of "%s"' % pkg['name'])
            return

        pkgname = pkg['name']
        srcdir = pkg['src']
        builddir = pkg['build']
        print('Building %s: ' % pkgname, end='')

        builtfile = os.path.exists(os.path.join(builddir, '.builder'))

        if os.path.exists(builddir) and os.path.isdir(builddir):
            if os.path.exists(builtfile) and os.path.isdir(builtfile):
                print(Gray('SKIP'))
                return

        if os.path.exists(os.path.join(srcdir, 'meson.build')):
            self._build_meson(pkg)
        elif os.path.exists(os.path.join(srcdir, 'autogen.sh')):
            self._build_autotools(pkg)
        elif os.path.exists(os.path.join(srcdir, 'CMakeLists.txt')):
            self._build_cmake(pkg)

        pkg['state']['built'] = True
        self._update_json(pkg)

        print(Green('DONE'))

    def _get_build_conf(self, pkg, buildtype):
        pkgname = pkg['name']

        buildconf = pkg['config'].get(buildtype)
        if buildconf is None:
            buildconf = PACKAGES[pkgname].get(buildtype)
            if buildconf is not None:
                pkg['config'][buildtype] = buildconf
                # if 'meson' options wasn't set into json (or it was None), but
                # it was set now in the default config, save it into json.
                self._update_json(pkg)
            else:
                buildconf = ''

        return buildconf

    def _build_meson(self, pkg):
        pkgname = pkg['name']
        self.logger.logln('Building %s with meson.' % pkgname)

        self._call_meson(pkg)
        self._call_ninja(pkg)

    def _call_meson(self, pkg):
        mesonopts = self._get_build_conf(pkg, 'meson')
        self.logger.logln('Build opts: "%s"' % mesonopts)

        cmd = ['meson']
        cmd.append('--prefix=%s' % self._inst_dir)
        if mesonopts:
            cmd.extend(mesonopts.split())
        cmd.append(pkg['build'])

        self._call(cmd, pkg['src'])

        pkg['state']['configured'] = True
        self._update_json(pkg)

    def _call_configure(self, pkg):
        autoopts = self._get_build_conf(pkg, 'autotools')
        self.logger.logln('Build opts: "%s"' % autoopts)

        cmd = ['./autogen.sh']
        self._call(cmd, pkg['src'])

        os.makedirs(pkg['build'], exist_ok=True)
        cmd = ['%s/configure' % pkg['src']]
        cmd.append('--prefix=%s' % self._inst_dir)
        if autoopts:
            cmd.extend(autoopts.split())
        self._call(cmd, pkg['build'])

        pkg['state']['configured'] = True
        self._update_json(pkg)

    def _call_ninja(self, pkg):
        cmd = ['ninja']
        self._call(cmd, pkg['build'])

        cmd.append('install')
        self._call(cmd, pkg['build'])

    def _call_make(self, pkg):
        cmd = ['make']
        cmd.append('-j%d' % os.cpu_count())
        self._call(cmd, pkg['build'])

        cmd.append('install')
        self._call(cmd, pkg['build'])

    def _call_cmake(self, pkg):
        cmakeopts = self._get_build_conf(pkg, 'cmake')
        self.logger.logln('Build opts: "%s"' % cmakeopts)

        os.makedirs(pkg['build'], exist_ok=True)
        cmd = ['cmake']
        cmd.append(pkg['src'])
        cmd.append('-DCMAKE_INSTALL_PREFIX=%s' % self._inst_dir)
        cmd.append('-GNinja')
        if cmakeopts:
            cmd.extend(cmakeopts.split())

        self._call(cmd, pkg['build'])

        pkg['state']['configured'] = True
        self._update_json(pkg)

    def _build_autotools(self, pkg):
        self.logger.logln('Building %s with autotools.' % pkg['name'])

        self._call_configure(pkg)
        self._call_make(pkg)

    def _build_cmake(self, pkg):
        self.logger.logln('Building %s with cmake.' % pkg['name'])

        self._call_cmake(pkg)
        self._call_ninja(pkg)

    def clean(self):
        print('Clean')

        self.logger.logln("Starting cleaning.")

        for p in self._pkgs:
            self._process_pkg(p, self._clean_pkg)

    def _clean_pkg(self, pkg):
        self.logger.logln('Cleaning package: ' + pkg['name'])
        cmd = ['git', 'clean', '-fdx']
        self._call(cmd, pkg['src'])

    def _call(self, cmd, cwd=None, env=None):
        if env is None:
            env = self._env

        if type(cmd) != type([]) or len(cmd) == 0:
            raise Exception('Invalid command to _call', cmd)

        self.logger.logln(' '.join(cmd))
        cmdprocess = subprocess.Popen(cmd, stdout=self.logger.get_file(),
                stderr=subprocess.STDOUT, universal_newlines=True,
                cwd=cwd, env=env)
        result = cmdprocess.wait()

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
