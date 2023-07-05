#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
 Authors:
   yifengyou <842056007@qq.com>
"""

import argparse
import datetime
import requests
import sys
from bs4 import BeautifulSoup

CURRENT_VERSION = "0.1.0"


def beijing_timestamp():
    utc_time = datetime.datetime.utcnow()
    beijing_tz = datetime.timezone(datetime.timedelta(hours=8))
    beijing_time = utc_time.astimezone(beijing_tz)
    return beijing_time.strftime("%Y/%m/%d %H:%M:%S")


def check_python_version():
    current_python = sys.version_info[0]
    if current_python == 3:
        return
    else:
        raise Exception('Invalid python version requested: %d' % current_python)


def get_file_links(url, quiet=False):
    file_links = []
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
            f.write(file_link + '\n')
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
    wget_m(args.url, args.manifest, args.quiet)
    end_time = beijing_timestamp()
    print(f"handle url done! {begin_time} - {end_time}")


def main():
    global CURRENT_VERSION
    check_python_version()

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-v", "--version", action="store_true",
                        help="show program's version number and exit")
    parser.add_argument("-h", "--help", action="store_true",
                        help="show this help message and exit")
    parser.add_argument("-u", "--url", default=None,
                        help="target url link")
    parser.add_argument("-m", "--manifest", default="manifest.txt",
                        help="manifest path")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="quiet output")
    parser.add_argument("--just-manifest", action="store_true",
                        help="only manifest")

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
    else:
        args.func(args)


if __name__ == "__main__":
    main()
