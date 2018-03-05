# PNG Recon

Hide arbitrary data in plain site. Stuff files in PNGs and retrieve them later.

Optionally compress data.

Optionally encrypt data with a symmetric key derived from a salted password.

# Install

1. Clone this repo.
2. Have `virtualenv` and `python3`
3. `virtualenv -p python3 venv`
4. `source venv/bin/activate`
5. `pip install -I .`
6. `pngrecon -h`

# Usage

In general: use the `encode` command to stuff a file into a PNG. Use `decode`
to retrieve it later.

By default, they both read from stdin and write to stdout.

Try `pngrecon encode -h` and `pngrecon decode -h` for a full list of options.

## Example usage

Demonstrates data can be encoded and then decoded successfully.

    (venv) user@host$ sha1sum README.md
    1e2e72803fe66b8cdc2e7bfdf1eba6cf64584d2a  README.md
    (venv) user@host$ <README.md pngrecon encode | pngrecon decode | sha1sum
    1e2e72803fe66b8cdc2e7bfdf1eba6cf64584d2a  -

# Common options

Pass `-c gzip` to `pngrecon encode` to compress encoded data with zlib.

    # README.md is 1245 bytes but the data chunk storing it is only 615 bytes
    (venv) user@host$ wc -c README.md
        1245 README.md
    (venv) user@host$ <README.md pngrecon encode -c gzip | pngrecon info
    /dev/stdin contains 5 chunks
    Chunk IHDR with len 13
    Chunk IDAT with len 10
    ChunkType.Index with len 12
    ChunkType.Data with len 615
    Chunk IEND with len 0

With `pngrecon encode`, give `-e` to encrypt the data using a symmetric key.
You may either give pngrecon a passphrase when prompted, or a `--key-file` from
which to read a passphrase.  **Note**: the *entire* contents of the
`--key-file` will be used, *including any trailing new line characters*.

    (venv) user@host$ echo -n "SuperSecurePassword" > pw.txt
    (venv) user@host$ <file.txt pngrecon encode -e --key-file pw.txt | pngrecon decode --key-file pw.txt
    [ ... contents of file.txt ... ]


Use `-i` and `-o` to change input/outout for `encode` and `decode` commands.

    (venv) user@host$ pngrecon encode -i README.md -o hidden-readme.png
    (venv) user@host$ file hidden-readme.png
    hidden-readme.png: PNG image data, 1 x 1, 1-bit grayscale, non-interlaced

## More examples

Encode all files in the current working directory with the help of `tar`.

    (venv) user@host$ tar c . | pngrecon encode > hidden-backup.tar.png
    (venv) user@host$ pngrecon info hidden-backup.tar.png
    hidden-backup.tar.png contains 5 chunks
    Chunk IHDR with len 13
    Chunk IDAT with len 10
    IndexChunk with len 12
    DataChunk with len 10362880
    Chunk IEND with len 0
    (venv) user@host$ pngrecon decode -i hidden-backup.tar.png | tar t
    [ ... list of files ... ]


# Ideas

- Add padding chunks.

  When in the image, they should look exactly like a data chunk. So the data
  chunk type needs to be more complex.

  Actually ... this seems quite hard. How big should the be? How many? Where
  in the file?

# Warnings

Instead of relying on pngrecon to use standard cryptography libraries
correctly, it might be better to use well-established and trusted encryption
tools before piping data into pngrecon. We think we are using these libraries
correctly, but if you need to rely on encryption, we think it is probably
smarter to use something written by cryptographers.

We sought advice regarding compressing *and* encrypting data. The consensus
seemed to be that compressing data and then encrypting the result is smarter
than the opposite. That said, in certain situations, if your adversary can
control part of the plaintext you are encrypting and can cause the
encryption+compression to happen over and over again, they can learn the
contents.
