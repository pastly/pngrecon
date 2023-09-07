#!/usr/bin/env bash
set -eu
T=$(mktemp -d)
function finish {
    rm -rf $T
}
trap finish EXIT

base="$(dirname $0)"
pushd $base>/dev/null
for D in ./*/; do
    # T - root temp directory (eg /tmp/tmp.xxxxxx)
    # D - this test's directory, with extra punc (eg ./001-basic/)
    # N - this test's directory name, with no punc (eg 001-basic)
    N="$(basename $D)"
    mkdir -p "$T/$D"
    pushd $D>/dev/null
    bash test.sh "$T/$D" && printf "OK   $N\n" || { printf "FAIL $N\n" ; exit 1; } &
    popd>/dev/null
done
popd>/dev/null
wait
printf "DONE :)\n"