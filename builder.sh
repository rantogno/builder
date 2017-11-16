#!/usr/bin/env bash

export SRCDIR="/home/rantogno/intel/work"
export WLD="/home/rantogno/usr"

export LD_LIBRARY_PATH="$WLD/lib:$WLD/lib64"
export PKG_CONFIG_PATH="$WLD/lib/pkgconfig/:$WLD/share/pkgconfig:$WLD/lib64/pkgconfig/"
export PATH="$WLD/bin:$PATH"
export ACLOCAL_PATH="$WLD/share/aclocal"
export ACLOCAL="aclocal -I $ACLOCAL_PATH"

export CMAKE_PREFIX_PATH=$WLD

export SSH_AUTH_SOCK="${XDG_RUNTIME_DIR}/gnupg/S.gpg-agent.ssh"

# export PATH="$HOME/depot_tools:$PATH"
# export DISPLAY=":0"

export VK_ICD_FILENAMES="$WLD/share/vulkan/icd.d/intel_icd.x86_64.json"

PACKAGES="\
	libunwind \

	libdrm \
	wayland \
	wayland-protocols \
	mesa-trunk \
	waffle \

	igt-gpu-tools \

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
"

wayland_CONF="--disable-documentation"
mesa_trunk_MESON="-Dplatforms=drm,x11,wayland,surfaceless -Ddri-drivers=i965 -Dgallium-drivers= -Dvulkan-drivers=intel -Dgbm=true"
libinput_MESON="-Dlibwacom=false -Ddocumentation=false -Ddebug-gui=false -Dtests=false"

libunwind_GIT="git://git.sv.gnu.org/libunwind.git"

libinput_GIT="git://anongit.freedesktop.org/wayland/libinput"

libdrm_GIT="git://anongit.freedesktop.org/drm/libdrm"
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

# Global options
force_install=false
fetch_first=false

get_auto_opts()
{
	local PKGOPTS
	eval PKGOPTS="\$${NNAME}_CONF"
	echo $PKGOPTS
}

get_meson_opts()
{
	local PKGOPTS
	eval PKGOPTS="\$${NNAME}_MESON"
	echo $PKGOPTS
}

build_autot()
{
	echo "Building $1 with autotools"
	local NNAME=$2
	local PKGOPTS=$(get_auto_opts $NNAME)

	if [ ! -x configure ]; then
		NOCONFIGURE=1 ./autogen.sh
	fi

	mkdir -p build
	pushd build

	../configure --prefix=$WLD $PKGOPTS
	make -j$(nproc) && make install

	popd
}

build_meson()
{
	echo "Building $1 with meson"
	local NNAME=$2
	local PKGOPTS=$(get_meson_opts $NNAME)

	meson --prefix=$WLD $PKGOPTS build
	ninja -C build/ install
}

build_cmake()
{
	echo "Building $1 with cmake"
	local NNAME=$2
	local PKGOPTS=$(get_meson_opts $NNAME)

	mkdir -p build
	pushd build

	cmake .. -DCMAKE_INSTALL_PREFIX=$WLD $PKGOPTS -GNinja
	popd

	ninja -C build/ install
}

build()
{
	local PKGNAME=$1
	echo "Building $PKGNAME..."
	
	local NNAME=${PKGNAME//-/_}

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
		build_meson $PKGNAME $NNAME
	elif [ -f autogen.sh ]; then
		build_autot $PKGNAME $NNAME
	elif [ -f CMakeLists.txt ]; then
		build_cmake $PKGNAME $NNAME
	else
		echo "Couldn't build $PKGNAME. Unknown build system."
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


fetch()
{
	local PKGNAME=$1

	local URL=$(get_repo_url $PKGNAME)

	if [ -z "$URL" ]; then
		echo "Can't fetch '$PKGNAME': url not defined."
		return -1
	fi

	echo "Fetching $PKGNAME: $URL"

	git clone $URL
}

process_install()
{
	echo "Installing packages: $@"
	echo "Force reinstall: $force_install, fetch: $fetch_first"

	mkdir -p $ACLOCAL_PATH

	if [ $# -eq "0" ]; then
		PKGS=$PACKAGES
	else
		PKGS=$@
	fi

	echo "Processing packages:"
	echo $PKGS

	pushd $SRCDIR

	for pkg in $PKGS; do
		if [[ ! -d "$pkg" ]] && [[ "$fetch_first" = true ]]; then
			fetch $pkg
		fi

		build $pkg || break
	done

	popd
}

sub_install()
{
	echo "Install: $@"
	while getopts ":hfg" opt; do
		case ${opt} in
			f)
				force_install=true
				;;
			g)
				fetch_first=true
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
	process_install $@
}

sub_uninstall()
{
	echo "Uninstall not implemented yet."
}

sub_clean()
{
	echo "Clean not implemented yet."
}

subcommand=$1
shift

case $subcommand in
	install)
		echo "Remaining args: $@"
		sub_install $@
		;;
	uninstall)
		echo "Remaining args: $@"
		sub_uninstall $@
		;;
	clean)
		echo "Remaining args: $@"
		sub_clean $@
		;;
esac
