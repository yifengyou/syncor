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
import subprocess
import sys
import urllib
from urllib.parse import unquote

import requests
import select
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
    else:
        perror(f"target manifest {args.download} is not found!")

    with open(args.download, 'r') as tf:
        urls = tf.readlines()
    urls_with_index = []
    total = len(urls)
    if args.prefix != "" and not args.prefix.startswith("/"):
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


def do_exe_cmd(cmd, print_output=False, shell=False):
    stdout_output = ''
    stderr_output = ''
    if isinstance(cmd, str):
        cmd = cmd.split()
    elif isinstance(cmd, list):
        pass
    else:
        raise Exception("unsupported type when run do_exec_cmd", type(cmd))

    # print("Run cmd:" + " ".join(cmd))
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=shell)
    while True:
        # 使用select模块，监控stdout和stderr的可读性，设置超时时间为0.1秒
        rlist, _, _ = select.select([p.stdout, p.stderr], [], [], 0.1)
        # 遍历可读的文件对象
        for f in rlist:
            # 读取一行内容，解码为utf-8
            line = f.readline().decode('utf-8').strip()
            # 如果有内容，判断是stdout还是stderr，并打印到屏幕，并刷新缓冲区
            if line:
                if f == p.stdout:
                    if print_output == True:
                        print("STDOUT", line)
                    stdout_output += line + '\n'
                    sys.stdout.flush()
                elif f == p.stderr:
                    if print_output == True:
                        print("STDERR", line)
                    stderr_output += line + '\n'
                    sys.stderr.flush()
        if p.poll() is not None:
            break
    return p.returncode, stdout_output, stderr_output


# 定义一个函数，接受一个目录作为参数
def check_rpm(dir, ff):
    # 遍历目录下的所有文件和子目录
    for file in os.listdir(dir):
        # 拼接完整的路径
        path = os.path.join(dir, file)
        # 如果是文件，且以.rpm结尾
        if os.path.isfile(path) and path.endswith(".rpm"):
            # 调用rpm -K命令检查rpm包是否完整
            retcode, stdout, stderr = do_exe_cmd(["rpm", "-K", "--nosignature", path], print_output=False, shell=False)
            if 0 != retcode:
                ff.write(f"{path} [{retcode}]\nSTDOUT:{stdout.strip()}\nSTDERR:{stderr.strip()}\n")
        # 如果是子目录，递归调用函数
        elif os.path.isdir(path):
            check_rpm(path, ff)


def handle_rpm_check(args):
    begin_time = beijing_timestamp()
    with open("check_failed.log", "w") as ff:
        check_rpm(args.check, ff)
    end_time = beijing_timestamp()
    print("check failed output to file: check_failed.log")
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
    parser.add_argument("-o", "--output", default="manifest.log",
                        help="setup output manifest path")
    parser.add_argument("-d", "--download", default=None,
                        help="download from url list")
    parser.add_argument("-j", "--job", default=os.cpu_count(), type=int,
                        help="job count")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="quiet output")
    parser.add_argument("-p", "--prefix", default='',
                        help="setup saving prefix")
    parser.add_argument("-c", "--check", default='',
                        help="verify rpm in target directory")

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
    elif args.check is not None:
        handle_rpm_check(args)
    else:
        args.func(args)


if __name__ == "__main__":
    main()
