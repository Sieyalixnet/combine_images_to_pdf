# About

This project can easily extract the pictures from recursive rar/zip(cbz) and combine them as a pdf respectively.
supported images format:".avif",".jpg",".jpeg",".bmp",".png"

Now only can used in `Windows`.

## Target

For example, `F:/books` contains

- book_many.rar
- book2.zip

and `book_many.rar` contains 

- book_many_1.rar/(many pics)
- book_many_2/(many pics)

all the file will extracted and combine as:

- ./output/book_many_1.pdf
- ./output/book_many_2.pdf
- ./output/book2.pdf

## before you used this script

1. set the environment variables

Add the path which contains `UnRAR` in environment variables. The `UnRAR` can be found in some softwares' path like `WinRAR`.

2. install requirment

use command: `python -m pip install -r .\requirments.txt`

## How to use

use command `python main.py -p {path of zipfile}`
in the above example, you can use `python main.py -p F:/books`.

## parameters

| parameters | description |
| ----|----|
|-p PATH, --path PATH |Base path of processing. Default: recent path|
|--no_copy|Do not copy existed pdf/epub/pictures from base path.|
|--no_clear|Do not remove the existed files of temp dir, target dir and output dir.|