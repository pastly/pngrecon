All values are stored in big-endian mode.

Nothing can be assumed about the order of these chunks in a PNG.

# Index Chunk

    deQm
    64 65 51 6d (hex)
    110 101 81 109 (decimal)

Appears exactly once in a PNG containing data encoded by pngrecon.

May appear anywhere in the list of chunks in the PNG.

It's presence MAY be used to quickly check if an image (i) definitely is not a
valid pngrecon image, or (ii) might be a valid pngrecon image.

## Fields

In this order, an index chunk contains the following fields.

### Encoding Type

`uint32`

Specifies the type of data stored in this file.

Valid values are:

- `1`: A single file

### Encryption Type

`uint32`

Specifies the type of encryption used on the source data stored in this file.

Valid values are:

- `1`: No encryption used
- `2`: Symmetric encryption using a salted password

### Compression Method

`uint32`

Specifies the type of compression used on the source data in this file.

Valid values are:

- `1`: No compression used
- `2`: Data is compressed using zlib (gzip)
- `3`: Data is compressed using lzma (xz)


### Number of Data Chunks

`uint32`

Specifies the number of data chunks that are in this file. The number may be
zero. If the actual number of data chunks does not match this, the file SHOULD
be considered invalid.

# Crypto Info Chunk

    yyBo
    79 79 42 6f (hex)
    121 121 66 111 (decimal)

Appears exactly zero or one times in a PNG containing pngrecon encoded data.

It MUST exist if encryption was used. It SHOULD NOT exist if encryption was not
used.

## Fields

In this order, a crypto info chunk contains the following fields.

### Salt

    char[16]

The random 16-byte salt used when generating an encryption key from the
user-supplied password.

# Data Chunk

    maTt
    6d 61 54 74 (hex)
    109 97 84 116 (decimal)

Appears between zero and 2^32-1 times in a PNG containing pngrecon encoded data.

During encoding, data is optionally compressed and optionally encrypted (in
that order). After that, it is broken up into a series of "bites", and each
"bite" is stored in a data chunk. A "bite" has a maximum size of 100 MiB in
this implementation, chosen rather arbitrarily, and which is significantly
smaller than the size limit of a chunk the PNG standard allows for (4 GiB,
limited by the max value of a uint32).

Encoders MAY choose almost any max size for a "bite" between 1 and *almost* 4
GiB. In fact, encoders MAY randomly size each "bite" within those limits.

Decoders MAY assume that if a data chunk exists, it will contain a "bite" with
positive size.  Decoders MUST NOT assume anything else such as number, size, or
order of data chunks.

## Fields

In this order, a data chunk contains the following fields.

### Index

`uint32`

**Any** `uint32`. The data chunks' indexes determine how they should be ordered
when decoding. Lower indexes come first. Data chunks MAY be stored in the PNG
in any order. Only the sorted order of indexes is important. For example, it is
**not an error** to store three data chunks with the indexes 43, 943, 88 as
long as the are meant to be reassembled in order (43, 88, 943) during decoding.

#### Data

`bytes`

One or more bytes storing the (possibly encrypted, and possibly compressed)
actual payload data from the user. These are the "bites" described previously.
