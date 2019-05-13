#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse, os
import os.path
import shutil
import shutil
import subprocess
import json

PKG_CMDS = ('install', 'clean')

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

class RepoConfig:
    def __init__(self):
        default = '~/.config/builder.conf'
        self._default_path = os.path.expanduser(default)
        try:
            config_file = open(self._default_path)
            self._config = json.load(config_file)
        except IOError:
            self._config = {
                    'repos': {},
                }

        self._use = None
        self._load_use()

    @property
    def use(self):
        return self._use

    def _check_base_path(self, path):
        builderpath = os.path.join(path, '.builder')
        if os.path.isdir(builderpath):
            pkglistpath = os.path.join(builderpath, 'pkglist.json')
            if os.path.exists(pkglistpath):
                return True
        return False

    def _find_base(self):
        path = os.path.curdir
        homedir = os.path.expanduser('~')

        while True:
            fullpath = os.path.abspath(path)
            # We don't want builddirs in root or home dir
            if fullpath == homedir or fullpath == '/':
                return None

            if self._check_base_path(fullpath):
                return fullpath

            path = os.path.join(path, '..')

    def _load_use(self):
        path = self._find_base()
        # if path is None:
        #     raise Exception("Couldn't find valid repo in the path: "
        #                     + os.path.abspath(os.path.curdir))

        repo = self.get_name(path)
        if repo is not None:
            self._use = repo

    def _update(self):
        os.makedirs(os.path.dirname(self._default_path), exist_ok=True)
        jsonfile = open(self._default_path, 'w')
        json.dump(self._config, jsonfile, indent=4)

    def list(self):
        print('Listing repos')
        repos = self._config['repos']
        for repo in repos:
            print('%15s : %s' % (repo, repos[repo]['path']))

        print()
        default_repo = self._use
        default_path = None
        if default_repo is not None:
            default_path = self.get_path(default_repo)
        print('Repo in use: %s (%s)' % (default_repo, default_path))

    def add(self, name, path):
        repos = self._config['repos']
        if name in repos:
            raise Exception('Repo %s already exists.' % name)

        repos[name] = { 'path': path }
        self._update()

    def remove(self, name):
        repos = self._config['repos']
        v = repos.pop(name, None)
        if v is None:
            print("Repo '%s' not found" % name)
            return

        if self.use == name:
            self.use = None
        self._update()

    def exist(self, repo):
        return repo in self._config['repos']

    def get_name(self, path):
        for k, v in self._config['repos'].items():
            if path == v['path']:
                return k
        return None

    def get_path(self, repo):
        return self._config['repos'][repo]['path']

class Pkg:
    def __init__(self, pkglist, name, basedir, logger, env):
        self.name = name
        self._logger = logger
        self._env = env
        self._pkglist = pkglist

        confdir = os.path.join(basedir, '.builder/pkgs')
        self.jsonpath = os.path.join(confdir, name + '.json')
        if os.path.exists(self.jsonpath):
            self._load_from(self.jsonpath)
        else:
            self._create_new(basedir)

        self._inst_dir = os.path.join(basedir, 'usr')

        pkgconf = self._pkglist[self.name]
        self._skipinstall = pkgconf.get('skipinstall', False)

        self._config = {
            'meson': pkgconf.get('meson'),
            'autotools': pkgconf.get('autotools'),
            'cmake': pkgconf.get('cmake'),
        }

        self._buildsystem = pkgconf.get('buildsystem')

        srcdir = os.path.join(basedir, 'src')
        workdir = os.path.join(basedir, '.workdir')

        self.srcpath = os.path.join(srcdir, self.name)
        self.buildpath = os.path.join(self.srcpath, 'build')

        self._skipped = True

    def _create_new(self, basedir):
        self._logger.logln('Creating new config for: %s' % self.name)

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

        self._configured = pkg['state']['configured']
        self._built = pkg['state']['built']

    def get_conf(self, conftype):
        return self._config.get(conftype)

    def _to_json(self):
        json_dict = {
            '__builder__': True,
            'name': self.name,
            'state': {
                'configured': self._configured,
                'built': self._built,
            },
        }

        return json_dict

    def update(self):
        jsonfile = open(self.jsonpath, 'w')
        json.dump(self, jsonfile, indent=4, default=Pkg._to_json)
        jsonfile.close()

    @property
    def built(self):
        return self._built

    @built.setter
    def built(self, val):
        self._built = val
        self.update()
        if val:
            self._skipped = False

    def __str__(self):
        return self.name

    def _call(self, cmd, cwd=None, env=None):
        if env is None:
            env = self._env

        if type(cmd) != type([]) or len(cmd) == 0:
            raise Exception('Invalid command to _call', cmd)

        self._logger.logln(' '.join(cmd))
        cmdprocess = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, universal_newlines=True,
                cwd=cwd, env=env)
        for line in cmdprocess.stdout:
            self._logger.log(line)
        result = cmdprocess.wait()

        if result != 0:
            raise Exception('Command failed', cmd, result)

    def _fetch(self):
        print('Fetching %s: ' % self.name, end='', flush=True)

        if os.path.exists(self.srcpath) and os.path.isdir(self.srcpath):
            print(Gray('SKIP'))
            return
        cmd = ['git', 'clone', self._pkglist[self.name]['uri'], self.srcpath]
        self._call(cmd)
        print(Green('DONE'))

    def _check_configured(self):
        if os.path.exists(self.buildpath) and os.path.isdir(self.buildpath):
            if self._configured and not self._force_configure:
                return True
        return False

    def _check_built(self):
        if os.path.exists(self.buildpath) and os.path.isdir(self.buildpath):
            if self._built and not self._force_build:
                # print(Gray('SKIP'))
                return True
        return False

    def _build(self):
        if self._skipinstall:
            self._logger.logln('Skipping install of "%s"' % self.name)
            return

        print('Building %s: ' % self.name, end='')

        build_func = {
            'meson': self._build_meson,
            'autotools': self._build_autotools,
            'cmake': self._build_cmake,
        }

        if self._buildsystem is not None:
            build_func[self._buildsystem]()
        elif os.path.exists(os.path.join(self.srcpath, 'meson.build')):
            build_func['meson']()
        elif os.path.exists(os.path.join(self.srcpath, 'autogen.sh')):
            build_func['autotools']()
        elif os.path.exists(os.path.join(self.srcpath, 'CMakeLists.txt')):
            build_func['cmake']()

        if self._skipped:
            print(Gray('SKIP'))
        else:
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
        if self._check_configured():
            return
        mesonopts = self.get_conf('meson')
        self._logger.logln('Build opts: "%s"' % mesonopts)

        cmd = ['meson']
        cmd.append('--prefix=%s' % self._inst_dir)
        if mesonopts:
            cmd.extend(mesonopts.split())
        cmd.append(self.buildpath)

        self._call(cmd, self.srcpath)

        self._configured = True
        self.built = False

    def _call_ninja(self):
        if self._check_built():
            return
        cmd = ['ninja']
        cmd += ['-C', self.buildpath]
        self._call(cmd, self.srcpath)

        cmd.append('install')
        self._call(cmd, self.srcpath)
        self.built = True

    def _call_configure(self):
        if self._check_configured():
            return
        autoopts = self.get_conf('autotools')
        self._logger.logln('Build opts: "%s"' % autoopts)

        # m4 workaround
        #
        # some packages have AC_CONFIG_MACRO_DIRS([m4]) or ACLOCAL_AMFLAGS = -I
        # m4 but the m4 dir doesn't exist in the original repo, causing
        # autogen.sh to fail. Let's just always create it, since it doesn't
        # hurt anything
        m4dir = os.path.join(self.srcpath, 'm4')
        os.makedirs(m4dir, exist_ok=True)

        cmd = ['./autogen.sh']
        self._call(cmd, self.srcpath)

        os.makedirs(self.buildpath, exist_ok=True)
        cmd = ['%s/configure' % self.srcpath]
        cmd.append('--prefix=%s' % self._inst_dir)
        if autoopts:
            cmd.extend(autoopts.split())
        self._call(cmd, self.buildpath)

        self._configured = True
        self.built = False

    def _call_make(self):
        if self._check_built():
            return
        cmd = ['make']
        cmd.append('-j%d' % os.cpu_count())
        self._call(cmd, self.buildpath)

        cmd.append('install')
        self._call(cmd, self.buildpath)
        self.built = True

    def _call_cmake(self):
        if self._check_configured():
            return
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
        self.built = False

    def install(self, build=False, configure=False):
        self._logger.logln('')
        self._logger.logln('Installing package: ' + self.name)

        self._force_build = build
        self._force_configure = configure

        self._fetch()
        self._build()

    def clean(self):
        self._logger.logln('')
        self._logger.logln('Cleaning package: ' + self.name)
        cmd = ['git', 'clean', '-fdx']
        if os.path.exists(self.srcpath):
            self._call(cmd, self.srcpath)
        if os.path.exists(self.buildpath):
            shutil.rmtree(self.buildpath, ignore_errors=True)
        os.remove(self.jsonpath)

class Builder:

    ENV_NAME = 'setup_env.sh'

    def __init__(self, args, repos):
        self.__args = args
        self._repos = repos

        if args.subparser in PKG_CMDS or args.subparser == 'env':
            reponame = args.repo
            if reponame is None:
                reponame = self._repos.use
            self.name = reponame
            path = self._repos.get_path(reponame)
            self._setup_base(path)
            self._check_base_valid()
            self._setup_env()

        self.process_options(args)

    def _setup_base(self, path=None):
        if path is None:
            path = os.path.curdir
        basedir = os.path.abspath(path)
        self._base_dir = basedir
        self._work_dir = os.path.join(basedir, '.builder')

    def _check_base_valid(self):
        if not os.path.exists(self._work_dir):
            raise Exception("'.buildder' directory doesn't exist under "
                    "current directory: '%s'" % self._base_dir)
        if not os.path.isdir(self._work_dir):
            raise Exception("%s is not a dir" % self._work_dir)

    def _load_pkg_list(self, path=None):
        if path is None:
            path = os.path.curdir

        path = os.path.abspath(path)
        pkgfile = open(path)
        self._pkglist = json.load(pkgfile)

    def process_options(self, args):
        self.__verbose = args.verbose

        if args.output is not None:
            self.__logfile = args.output

        self.__command = args.subparser

        if args.subparser not in PKG_CMDS:
            return

        self._load_pkg_list(os.path.join(self._work_dir, 'pkglist.json'))
        self.process_packages(args.packages)

    def process_packages(self, packages):
        self.check_packages(packages)

        if len(packages) == 0:
            packages = self._pkglist.keys()

        self._pkgs = list(packages)

        print('packages:', Gray(str(self._pkgs)))

    def check_packages(self, packages):
        invalid = []
        for pkg in packages:
            if pkg not in self._pkglist:
                invalid.append(pkg)

        if len(invalid) > 0:
            raise Exception('Invalid packages: ' + str(invalid))

    def run(self):
        if self.__command in PKG_CMDS:
            # logger disabled when initializing repo
            self._logfile = os.path.join(self._base_dir, 'builder.log')
            self.logger = Logger(self._logfile, self.__verbose)
        operation = {
                'init': self.initialize,
                'install': self.install,
                'clean': self.clean,
                'remove': self.remove,
                'env': self.print_env,
                }

        operation[self.__command]()

    def _setup_env(self):
        basedir = self._base_dir
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

        aclocalpath = os.path.join(usr, 'share/aclocal')
        env['ACLOCAL_PATH'] = aclocalpath
        env['ACLOCAL'] = 'aclocal -I ' + aclocalpath

        env['CMAKE_PREFIX_PATH'] = usr
        env['NOCONFIGURE'] = '1'

        self._env = env

    def _write_env_file(self):
        envpath = os.path.join(self._inst_dir, self.ENV_NAME)

        content = '#!/usr/bin/env bash\n\n'
        content += self._env_content()

        envfile = open(envpath, 'w')
        envfile.write(content)
        envfile.close()

    def _print_env_eval(self):
        print(self._env_content('; '))

    def _env_content(self, endl='\n'):
        content = 'export WLD=%s' % self._inst_dir + endl
        content += 'export LD_LIBRARY_PATH="$WLD/lib:$WLD/lib64"' + endl

        content += 'export PKG_CONFIG_PATH="'
        content += '$WLD/lib/pkgconfig:'
        content += '$WLD/lib64/pkgconfig:'
        content += '$WLD/share/pkgconfig"' + endl

        content += 'export PATH="$WLD/bin:$PATH"' + endl
        content += 'export ACLOCAL_PATH="$WLD/share/aclocal"' + endl
        content += 'export ACLOCAL="aclocal -I $ACLOCAL_PATH"' + endl

        content += 'export CMAKE_PREFIX_PATH=$WLD' + endl

        content += 'export VK_ICD_FILENAMES='
        content += '"$WLD/share/vulkan/icd.d/intel_icd.x86_64.json"' + endl

        content += 'export PIGLIT_PLATFORM=gbm' + endl

        name = '(' + self.name + ')'

        content += 'PS1="' + name + ' $PS1"'

        return content

    def _make_dirs(self):
        self.logger.logln('Creating src, build and install dirs.')
        os.makedirs(self._src_dir, exist_ok=True)
        os.makedirs(self._build_dir, exist_ok=True)
        os.makedirs(self._inst_dir, exist_ok=True)
        os.makedirs(self._env['ACLOCAL_PATH'], exist_ok=True)

    def _process_pkg(self, pkgname, operation):
        self.logger.logln('')

        pkg = Pkg(self._pkglist, pkgname,
                self._base_dir, self.logger, self._env)

        operation(pkg)

    def initialize(self):
        repo_name = self.__args.name
        if self._repos.exist(repo_name):
            print("Repo '%s' already exists." % repo_name)
            print("If not, try removing it first.")
            return

        self._setup_base(self.__args.path)
        os.makedirs(self._work_dir, exist_ok=True)
        pkgspath = os.path.join(self._work_dir, 'pkgs')
        os.makedirs(pkgspath, exist_ok=True)

        jsonfile = os.path.join(self._work_dir, 'pkglist.json')
        shutil.copyfile(self.__args.jsonfile, jsonfile)
        self._repos.add(repo_name, self._base_dir)

    def remove(self):
        repo_name = self.__args.repo_name
        self._repos.remove(repo_name)

    def print_env(self):
        self._print_env_eval()

    def install(self):
        print('Install')

        self._make_dirs()

        self._write_env_file()

        self.logger.logln("Starting build.")

        for p in self._pkgs:
            self._process_pkg(p, self._inst_pkg)

    def _inst_pkg(self, pkg):
        force_build = self.__args.build
        force_configure = self.__args.configure
        pkg.install(build=force_build, configure=force_configure)
        return

    def clean(self):
        print('Clean')

        self.logger.logln("Starting cleaning.")

        for p in self._pkgs:
            self._process_pkg(p, self._clean_pkg)

    def _clean_pkg(self, pkg):
        self.logger.logln('Cleaning package: ' + str(pkg))
        pkg.clean()

def main():
    parser = argparse.ArgumentParser(description='Builder for mesa')
    parser.add_argument('--verbose', '-v', action='store_true')
    parser.add_argument('--output', '-o', help='log file')
    parser.add_argument('--repo', '-r', help='repo to use')

    pkg_parser = argparse.ArgumentParser(add_help=False)
    pkg_parser.add_argument('packages', metavar='PKG', type=str, nargs='*',
            help='package to process')

    commands = parser.add_subparsers(help='commands to run', dest='subparser')

    # Initialization
    init_p = commands.add_parser('init',
            help='initialize build environment')
    init_p.add_argument('name', type=str,
            help='name of this repo')
    init_p.add_argument('path', type=str, nargs='?',
            help='path to initialize builder')
    init_p.add_argument('--jsonfile', '-f', required=True,
            help='json file used to initialize')

    # Use this directory
    use_p = commands.add_parser('use',
            help='use this build environment')
    use_p.add_argument('repo_name', type=str,
            help='repo to start using')

    # Use this directory
    use_p = commands.add_parser('remove',
            help='use this build environment')
    use_p.add_argument('repo_name', type=str,
            help='repo to remove')

    # Print env
    use_p = commands.add_parser('env',
            help='output env setup')

    # Install packages
    install_p = commands.add_parser('install',
            parents=[pkg_parser],
            help='build and install packages')

    install_p.add_argument('--build', '-b', action='store_true',
            help='force rebuild package if already built')

    install_p.add_argument('--configure', '-c', action='store_true',
            help='force reconfigure package if already configured')

    # Clean packages
    clean_p = commands.add_parser('clean',
            parents=[pkg_parser],
            help='clean package source dir')

    args = parser.parse_args()

    repos = RepoConfig()

    if args.subparser is None:
        repos.list()
        return

    if repos.use is None:
        if args.repo is None and args.subparser in PKG_CMDS:
            print('No default repo set, need to specify one.')
            print('Use option --repo')
            return

    builder = Builder(args, repos)
    builder.run()

if __name__ == '__main__':
    main()
