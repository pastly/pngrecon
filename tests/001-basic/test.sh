set -eu
OUTDIR="$1"
pngrecon encode -i input.txt | pngrecon decode -o $OUTDIR/output.txt
s1=$(sha1sum input.txt | cut -d ' ' -f 1)
s2=$(sha1sum $OUTDIR/output.txt | cut -d ' ' -f 1)
[[ "$s1" = "$s2" ]]