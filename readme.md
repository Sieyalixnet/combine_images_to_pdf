# 关于本项目

ENGLISH: [en-US](./readme_EN.md)

这个项目可以递归地把rar/zip(cbz)中图片全部解压出来(即使压缩包内有另一个压缩包)，并将这些图片分别合成一个pdf。
默认支持的图片格式:".avif",".jpg",".jpeg",".bmp",".png"

暂时仅可在`Windows`下使用。

## 效果

简单来说假如`F:/books`内有

- book_many.rar
- book2.zip

而`book_many.rar`中有

- book_many_1.rar/(许多图片)
- book_many_2/(许多图片)

会全部解压后合成为

- ./output/book_many_1.pdf
- ./output/book_many_2.pdf
- ./output/book2.pdf

## 使用前置工作

1. 设置环境变量

需要把`UnRAR`加入到环境变量中，其一般在`WinRAR`等软件的安装目录

比如`WinRAR`安装在了`C:\Program Files\WinRAR`，复制该地址，我的电脑(右键)-属性-高级系统设置-环境变量-Path中新建一项并粘贴该地址。详情请参考一些环境变量的教程。

2. 安装依赖

使用命令`python -m pip install -r .\requirments.txt`

## 使用

只需要使用命令`python main.py -p {压缩包所在地址}`即可。

比如上述例子的`python main.py -p F:/books`。

## 参数

| 参数 | 说明 |
| ----|----|
|-p PATH, --path PATH|处理的根目录，默认为本脚本所在位置|
|--no_copy|若使用该参数，将不复制已存在于根目录的pdf/epub/各种格式的图片|
|--no_clear|若使用该参数，将不会移除处理过程中的和输出的文件夹|

