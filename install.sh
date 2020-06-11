#!/bin/sh

# delete existing vnstat
apk del --purge --no-cache vnstat

{ 
    apk add --no-cache vnstat~="${1}" >/dev/null 2>&1 && exit 0;
} || {
    apk add --no-cache --virtual=vnstat-build \
        sqlite-dev \
        gd-dev \
        build-base \
        coreutils \
        libjpeg-turbo-dev \
        libpng-dev

    tmpdir=$(mktemp -d)
    cd "$tmpdir" || exit

    wget http://humdi.net/vnstat/vnstat-"${1}".tar.gz -O - | tar -xzvf - --strip-components=1

    # https://github.com/alpinelinux/aports/blob/master/community/vnstat/APKBUILD
    ./configure \
        --prefix=/usr \
        --sysconfdir=/etc \
        --mandir=/usr/share/man \
        --infodir=/usr/share/info

    make && make install

    apk del --purge --no-cache vnstat-build
    apk add --no-cache libgd

    rm -rf "$tmpdir"
}
