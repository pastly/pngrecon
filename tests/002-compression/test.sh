set -eu
OUTDIR="$1"
pngrecon encode         -i input.txt | pngrecon decode -o $OUTDIR/o1
pngrecon encode -c      -i input.txt | pngrecon decode -o $OUTDIR/o2
pngrecon encode -c no   -i input.txt | pngrecon decode -o $OUTDIR/o3
pngrecon encode -c gzip -i input.txt | pngrecon decode -o $OUTDIR/o4
pngrecon encode -c xz   -i input.txt | pngrecon decode -o $OUTDIR/o5
s=$(sha1sum input.txt | cut -d ' ' -f 1)
s1=$(sha1sum $OUTDIR/o1 | cut -d ' ' -f 1)
s2=$(sha1sum $OUTDIR/o2 | cut -d ' ' -f 1)
s3=$(sha1sum $OUTDIR/o3 | cut -d ' ' -f 1)
s4=$(sha1sum $OUTDIR/o4 | cut -d ' ' -f 1)
s5=$(sha1sum $OUTDIR/o5 | cut -d ' ' -f 1)
[[ "$s" = "$s1" ]]
[[ "$s" = "$s2" ]]
[[ "$s" = "$s3" ]]
[[ "$s" = "$s4" ]]
[[ "$s" = "$s5" ]]