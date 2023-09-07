set -eu
OUTDIR="$1"

N=3
pngrecon encode --buffer-max-bytes 2 -i input.txt | pngrecon info > $OUTDIR/o
(( $(grep --count 'ChunkType.Data' $OUTDIR/o) == $N ))
grep --quiet "Claiming $N data chunks" $OUTDIR/o


N=1
pngrecon encode --buffer-max-bytes 1000 -i input.txt | pngrecon info > $OUTDIR/o
(( $(grep --count 'ChunkType.Data' $OUTDIR/o) == $N ))
grep --quiet "Claiming $N data chunks" $OUTDIR/o

N=1
pngrecon encode -i input.txt | pngrecon info > $OUTDIR/o
(( $(grep --count 'ChunkType.Data' $OUTDIR/o) == $N ))
grep --quiet "Claiming $N data chunks" $OUTDIR/o