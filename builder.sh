#!/usr/bin/env bash

if [ -n "$WLD" ]; then
    echo "WLD already set: $WLD"
    echo "Please run this script with a clean env."
    exit 5
fi

export SRCDIR="/home/rantogno/intel/work"
export WLD="/home/rantogno/usr"

export LD_LIBRARY_PATH="$WLD/lib:$WLD/lib64"
export PKG_CONFIG_PATH="$WLD/lib/pkgconfig/:$WLD/share/pkgconfig:$WLD/lib64/pkgconfig/"
export PATH="$WLD/bin:$PATH"
export ACLOCAL_PATH="$WLD/share/aclocal"
export ACLOCAL="aclocal -I $ACLOCAL_PATH"

export CMAKE_PREFIX_PATH=$WLD

# export PATH="$HOME/depot_tools:$PATH"
# export DISPLAY=":0"

export VK_ICD_FILENAMES="$WLD/share/vulkan/icd.d/intel_icd.x86_64.json"

PACKAGES="\
    libunwind \

    libdrm \
    wayland \
    wayland-protocols \
    mesa \
    waffle \

    piglit \

    igt-gpu-tools \

    crucible \

    libinput \
    libepoxy \

    macros \
    x11proto \
    libxtrans \
    libX11 \
    libXext \
    dri2proto \
    glproto \
    libpciaccess \
    pixman \
    xkeyboard-config \
    xkbcomp \
    xserver \
    weston \
    "

# Build options
wayland_CONF="--disable-documentation"
mesa_MESON="-Dplatforms=drm,x11,wayland,surfaceless -Ddri-drivers=i965 -Dgallium-drivers= -Dvulkan-drivers=intel -Dgbm=true"
libinput_MESON="-Dlibwacom=false -Ddocumentation=false -Ddebug-gui=false -Dtests=false"
weston_CONF="--disable-setuid-install --enable-clients --enable-demo-clients-install"

# Special options
piglit_SKIPINSTALL=true
piglit_BUILDSRCDIR=true
piglit_SKIPALL=true

crucible_SKIPINSTALL=true
crucible_BUILDSRCDIR=true
crucible_SKIPALL=true

# Repositories
libunwind_GIT="git://git.sv.gnu.org/libunwind.git"

libinput_GIT="git://anongit.freedesktop.org/wayland/libinput"

libdrm_GIT="git://anongit.freedesktop.org/drm/libdrm"

wayland_GIT="git://anongit.freedesktop.org/wayland/wayland"
wayland_protocols_GIT="git://anongit.freedesktop.org/wayland/wayland-protocols"

mesa_GIT="git://anongit.freedesktop.org/mesa/mesa"

waffle_GIT="git@github.com:waffle-gl/waffle.git"
piglit_GIT="git://anongit.freedesktop.org/piglit"

igt_gpu_tools_GIT="git://anongit.freedesktop.org/drm/igt-gpu-tools"

crucible_GIT="git://anongit.freedesktop.org/mesa/crucible"

macros_GIT="git://git.freedesktop.org/git/xorg/util/macros"
x11proto_GIT="git://git.freedesktop.org/git/xorg/proto/x11proto"
libxtrans_GIT="git://git.freedesktop.org/git/xorg/lib/libxtrans"
libX11_GIT="git://git.freedesktop.org/git/xorg/lib/libX11"
libXext_GIT="git://git.freedesktop.org/git/xorg/lib/libXext"
dri2proto_GIT="git://git.freedesktop.org/git/xorg/proto/dri2proto"
glproto_GIT="git://git.freedesktop.org/git/xorg/proto/glproto"
libpciaccess_GIT="git://git.freedesktop.org/git/xorg/lib/libpciaccess"
pixman_GIT="git://git.freedesktop.org/git/pixman"
xserver_GIT="git://git.freedesktop.org/git/xorg/xserver"
libepoxy_GIT="https://github.com/anholt/libepoxy.git"
xkbcomp_GIT="git://anongit.freedesktop.org/xorg/app/xkbcomp"
xkeyboard_config_GIT="git://anongit.freedesktop.org/xkeyboard-config"
weston_GIT="git://anongit.freedesktop.org/wayland/weston"

# Global options
force_install=false
no_fetch=false
force_reconfigure=false

print_color()
{
    local color=$1
    shift
    local newline=$2
    shift
    local msg=$@
    local nlopt=""

    if [ "$newline" = false ]; then
        nlopt="-n"
    fi

    echo -e $nlopt "${color}${msg}"
    tput sgr0
}

print_bold_ln()
{
    print_color "\033[1m" true "$@"
}

print_bold()
{
    print_color "\033[1m" false "$@"
}

print_blue_ln()
{
    print_color "\E[34m" true "$@"
}

print_blue()
{
    print_color "\E[34m" false "$@"
}

print_red_ln()
{
    print_color "\E[31m" true "$@"
}

print_red()
{
    print_color "\E[31m" false "$@"
}

print_green_ln()
{
    print_color "\E[32m" true "$@"
}

print_green()
{
    print_color "\E[32m" false "$@"
}

print_yellow_ln()
{
    print_color "\E[33m" true "$@"
}

print_yellow()
{
    print_color "\E[33m" false "$@"
}

get_pkg_opts()
{
    local NNAME=$1
    local OPTNAME=$2
    local PKGOPTS
    eval PKGOPTS="\$${NNAME}_${OPTNAME}"
    echo $PKGOPTS
}

get_auto_opts()
{
    get_pkg_opts $1 "CONF"
}

get_meson_opts()
{
    get_pkg_opts $1 "MESON"
}

build_autot()
{
    echo "Building $1 with autotools"
    local NNAME=$2
    local PKGOPTS=$(get_auto_opts $NNAME)
    local success=false
    local skip_install=$(get_pkg_opts $NNAME SKIPINSTALL)
    local buildsrcdir=$(get_pkg_opts $NNAME BUILDSRCDIR)

    if [ "$buildsrcdir" == true ]; then
        builddir="."
    else
        builddir="build"
    fi


    if [[ ! -x configure ]] || [[ "$force_reconfigure" = true ]]; then
        NOCONFIGURE=1 ./autogen.sh
        if $? ; then
            echo "Failed to reconfigure package: $$1"
            return -1
        fi
    fi

    mkdir -p $builddir
    pushd $builddir

    $SRCDIR/$PKGNAME/configure --prefix=$WLD $PKGOPTS &&
        make -j$(nproc) && success=true

    if [[ "$success" = true ]] && [[ "$skip_install" != true ]]; then
        make install || success=false
    fi

    popd

    if [ "$success" = false ]; then
        return -1
    fi
}

build_meson()
{
    echo "Building $1 with meson"
    local NNAME=$2
    local PKGOPTS=$(get_meson_opts $NNAME)
    local skip_install=$(get_pkg_opts $NNAME SKIPINSTALL)

    # meson does not support/need BUILDSRCDIR

    meson --prefix=$WLD $PKGOPTS build || return -1
    [ "$skip_install" != true ] && ninja -C build/ install
}

build_cmake()
{
    echo "Building $1 with cmake"
    local NNAME=$2
    local PKGOPTS=$(get_meson_opts $NNAME)
    local success=true
    local skip_install=$(get_pkg_opts $NNAME SKIPINSTALL)
    local buildsrcdir=$(get_pkg_opts $NNAME BUILDSRCDIR)

    if [ "$buildsrcdir" == true ]; then
        builddir="."
    else
        builddir="build"
    fi

    mkdir -p $builddir
    pushd $builddir

    cmake "$SRCDIR/$PKGNAME" -DCMAKE_INSTALL_PREFIX=$WLD $PKGOPTS -GNinja || success=false

    popd

    if [ "$success" = true ]; then
        ninja -C $builddir
    fi

    if [[ "$success" = true ]] && [[ "$skip_install" != true ]]; then
        ninja -C $builddir install || success=false
    fi

    if [ "$success" = false ]; then
        return -1
    fi
}

build()
{
    local PKGNAME=$1
    local NNAME=$2
    echo "Building $PKGNAME..."

    local pkgdir="$SRCDIR/$PKGNAME"

    if [ ! -d $pkgdir ]; then
        echo "Can't build $PKGNAME: src dir '$pkgdir' doesn't exist."
        return -1
    fi

    pushd $SRCDIR/$PKGNAME

    if [ -d build/ -a $force_install = false ]; then
        popd
        return 0
    fi

    if [ -f meson.build ]; then
        build_meson $PKGNAME $NNAME || return -1
    elif [ -f autogen.sh ]; then
        build_autot $PKGNAME $NNAME || return -1
    elif [ -f CMakeLists.txt ]; then
        build_cmake $PKGNAME $NNAME || return -1
    else
        echo "Couldn't build $PKGNAME. Unknown build system."
        popd
        return -1
    fi

    popd
}

get_repo_url()
{
    local NNAME=${1//-/_}
    local URL
    eval URL="\$${NNAME}_GIT"
    echo $URL
}

check_fetch()
{
    local pkgname=$1
    local URL=$2

    if [ -d "$SRCDIR/$pkgname" ]; then
        return 1
    fi

    if [ -z "$URL" ]; then
        echo "Can't fetch '$pkgname': url not defined."
        return 2
    fi

    return 0
}

fetch()
{
    local PKGNAME=$1

    local URL=$(get_repo_url $PKGNAME)

    echo "Fetching $PKGNAME ($URL): "

    check_fetch $PKGNAME $URL
    local result=$?

    if [ "$result" != 0 ]; then
        return $result
    fi

    git clone $URL "$SRCDIR/$PKGNAME"
}

func_install()
{
    local pkgname=$1
    local NNAME=$2
    local result=0
    local fetch_result=0

    mkdir -p $ACLOCAL_PATH

    # Fetching source
    echo -n "Fetching ${pkgname}: "

    if [ "$no_fetch" = false ]; then
        fetch $pkg >&3 2>&1
        result=$?
    fi

    case $result in
        0)
            print_green_ln "DONE"
            ;;
        1)
            print_bold_ln "SKIP"
            ;;
        2)
            print_yellow_ln "SKIP - NO URL"
            fetch_result=2
            ;;
        *)
            print_red_ln "ERROR"
            fetch_result=3
            ;;
    esac

    if [ "$fetch_result" != 0 ]; then
        return $fetch_result
    fi

    # Building project
    echo -n "Building $pkgname: "

    result=0
    build $pkg $NNAME >&3 2>&1
    result=$?

    case $result in
        0)
            print_green_ln "DONE"
            ;;
        1)
            print_bold_ln "SKIP"
            ;;
        *)
            print_red_ln "ERROR"
            result=3
            ;;
    esac

    return $result
}

func_clean()
{
    local pkgname=$1
    local NNAME=$2

    if [[ -d "$SRCDIR/$pkgname" ]]; then
        pushd "$SRCDIR/$pkgname"
        git clean -fdx
        popd
    fi
}

process_packages()
{
    local process_all=false
    local call_func=$1

    shift

    if [ $# -eq "0" ]; then
        PKGS=$PACKAGES
        process_all=true
    else
        PKGS=$@
    fi

    echo
    echo "Processing packages:"
    echo
    print_bold_ln $PKGS
    echo

    for pkg in $PKGS; do
        local NNAME=${pkg//-/_}
        local skipall=$(get_pkg_opts $NNAME SKIPALL)
        if [[ "$skipall" = true ]] && [[ "$process_all" = true ]]; then
            continue
        fi

        # call command
        $call_func $pkg $NNAME 3> "/tmp/builder/${pkg}_log.txt"
        if [ "$?" != 0 ]; then
            break
        fi
    done
}

parse_install()
{
    echo "Installing packages: $@"

    while getopts ":hfgc" opt; do
        case ${opt} in
            f)
                force_install=true
                ;;
            g)
                no_fetch=true
                ;;
            c)
                force_reconfigure=true
                ;;
            \?)
                echo "Invalid option: -$OPTARG" 1>&2
                exit 1
                ;;
            h)
                echo "Usage: builder.sh install <options> packages"
                exit 0
                ;;
        esac
    done
    shift $((OPTIND -1))

    echo "Force reinstall: $force_install, fetch: $no_fetch"
    process_packages func_install $@
}

parse_uninstall()
{
    echo "Uninstall not implemented yet."
}

parse_clean()
{
    while getopts ":h" opt; do
        case ${opt} in
            \?)
                echo "Invalid option: -$OPTARG" 1>&2
                exit 1
                ;;
            h)
                echo "Usage: builder.sh clean packages"
                exit 0
                ;;
        esac
    done
    shift $((OPTIND -1))

    process_packages func_clean $@
}

subcommand=$1
shift

case $subcommand in
    install)
        echo "Remaining args: $@"
        parse_install $@
        ;;
    uninstall)
        echo "Remaining args: $@"
        parse_uninstall $@
        ;;
    clean)
        echo "Remaining args: $@"
        parse_clean $@
        ;;
esac
