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
	libdrm \
	wayland \
	wayland-protocols \
	mesa-trunk \
	waffle \
"

wayland_CONF="--disable-documentation"
mesa_trunk_MESON="-Dplatforms=drm,x11,wayland,surfaceless -Ddri-drivers=i965 -Dgallium-drivers= -Dvulkan-drivers=intel -Dgbm=true"

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

	../configure --prefix=$WLD $OPTS
	make -j8 && make install

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

	pushd $SRCDIR/$PKGNAME

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

mkdir -p $ACLOCAL_PATH

if [ $# -eq "0" ]; then
	PKGS=$PACKAGES
else
	PKGS=$@
fi

echo "Processing packages:"
echo $PKGS

for pkg in $PKGS; do
	build $pkg
done
