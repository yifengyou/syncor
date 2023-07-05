#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
 Authors:
   yifengyou <842056007@qq.com>
"""

import argparse
import datetime
import multiprocessing
import os.path
import shutil
import sys
import urllib
from urllib.parse import unquote

import requests
from bs4 import BeautifulSoup

CURRENT_VERSION = "0.1.0"


def beijing_timestamp():
    utc_time = datetime.datetime.utcnow()
    beijing_tz = datetime.timezone(datetime.timedelta(hours=8))
    beijing_time = utc_time.astimezone(beijing_tz)
    return beijing_time.strftime("%Y/%m/%d %H:%M:%S")


def perror(str):
    print("Error: ", str)
    sys.exit(1)


def check_python_version():
    current_python = sys.version_info[0]
    if current_python == 3:
        return
    else:
        raise Exception('Invalid python version requested: %d' % current_python)


def get_file_links(url, quiet=False):
    file_links = []
    # print(f"url {url}")
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        links = soup.find_all('a')
        for link in links:
            href = link.get('href')
            # 忽略目录，只解析页面文件
            if href.endswith('/'):
                continue
            file_link = requests.compat.urljoin(url, href)
            if not quiet:
                print(f"url : {file_link}")
            file_links.append(file_link)
    return file_links


def wget_m(url, filename, quiet=False):
    with open(filename, 'a') as f:
        file_links = get_file_links(url, quiet)
        for file_link in file_links:
            f.write(unquote(file_link) + '\n')
        response = requests.get(url)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            links = soup.find_all('a')
            for link in links:
                href = link.get('href')
                if href == "../":
                    # print(" ignore ../")
                    continue
                if href.endswith('/'):
                    # 拼接完整的子目录链接，使用urljoin方法，自动处理相对路径和绝对路径的问题
                    sub_url = requests.compat.urljoin(url, href)
                    # 递归地调用wget_m函数，传入子目录链接和文件名作为参数
                    wget_m(sub_url, filename, quiet)


def handle_url(args):
    begin_time = beijing_timestamp()
    if args.quiet:
        print("try download in quiet")
    else:
        print("try download ....")
    wget_m(args.url, args.output, args.quiet)
    end_time = beijing_timestamp()
    print(f"handle url done! {begin_time} - {end_time}")


def process_per_url(urls_with_index):
    (index, total, prefix, url) = urls_with_index
    url = unquote(url)
    name = os.path.basename(url)
    dir_name = os.path.join(prefix, os.path.dirname(url).replace("https://", '').replace("http://", ''))
    file_name = os.path.join(dir_name, name)
    print(f"file name: {file_name}")

    os.makedirs(dir_name, exist_ok=True)

    file_size = os.path.getsize(file_name) if os.path.exists(file_name) else 0
    request = urllib.request.Request(url)
    request.add_header("Range", "bytes={}-".format(file_size))

    with urllib.request.urlopen(request) as response, open(file_name, "ab") as file:
        shutil.copyfileobj(response, file)
    print(f"[ {index}/{total} ] Save to: {file_name}")


def handle_download(args):
    begin_time = beijing_timestamp()
    if os.path.isfile(args.download):
        print(f"target manifest is {args.download}")
    with open(args.download, 'r') as tf:
        urls = tf.readlines()
    urls_with_index = []
    total = len(urls)
    if not args.prefix.startswith("/"):
        perror("prefix must start with /")

    for i, url in enumerate(urls):
        url = url.strip()
        if url.startswith("http"):
            urls_with_index.append(
                (i + 1, total, args.prefix, url)
            )

    pool = multiprocessing.Pool(args.job)
    pool.imap_unordered(process_per_url, urls_with_index)

    pool.close()
    pool.join()
    end_time = beijing_timestamp()
    print(f"handle download done! {begin_time} - {end_time}")


def main():
    global CURRENT_VERSION
    check_python_version()

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-v", "--version", action="store_true",
                        help="show program's version number and exit")
    parser.add_argument("-h", "--help", action="store_true",
                        help="show this help message and exit")
    parser.add_argument("-u", "--url", default=None,
                        help="target url link without parent")
    parser.add_argument("-o", "--output", default="manifest.txt",
                        help="setup output manifest path")
    parser.add_argument("-d", "--download", default=None,
                        help="download from url list")
    parser.add_argument("-j", "--job", default=os.cpu_count(), type=int,
                        help="job count")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="quiet output")
    parser.add_argument("-p", "--prefix", default='',
                        help="setup saving prefix")

    # 开始解析命令
    args = parser.parse_args()

    if args.version:
        print("syncor %s" % CURRENT_VERSION)
        sys.exit(0)
    elif args.help or len(sys.argv) < 2:
        parser.print_help()
        sys.exit(0)
    elif args.url is not None:
        handle_url(args)
    elif args.download is not None:
        handle_download(args)
    else:
        args.func(args)


if __name__ == "__main__":
    main()
