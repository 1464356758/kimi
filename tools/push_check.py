#!/usr/bin/env python3
"""推送前自检：对 book/ 与 online/ 的实际文件计算 Git blob 哈希，供与远端目录回读逐项比对。

用法：
    python3 tools/push_check.py                 # 检查当前目录的 book/ 与 online/
    python3 tools/push_check.py /path/to/root   # 指定小说根目录

检查项：
1. 每个 JSON 文件必须以换行结尾且可解析（与 novel.py encoded() 的输出一致；
   远端比对失败多因推送时丢了这一字节）。
2. book/chapters/ 下冻结文件名中的 SHA256 必须与内容一致。
3. 打印 路径 -> blob sha1 对照表，与 GitHub 目录回读的 sha 字段逐项核对，
   全部一致才允许报告已保存。
"""
import hashlib
import json
from pathlib import Path
import sys


def blob_sha(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def collect(root):
    paths = []
    for name in ("book", "online"):
        base = root / name
        if base.is_dir():
            paths.extend(p for p in sorted(base.rglob("*")) if p.is_file())
    return [p for p in paths if "__pycache__" not in p.parts and p.name != ".novel.lock"]


def main():
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(".").resolve()
    problems = []
    rows = []
    for p in collect(root):
        data = p.read_bytes()
        rel = p.relative_to(root).as_posix()
        rows.append((rel, blob_sha(data), len(data)))
        if p.suffix == ".json":
            if not data.endswith(b"\n"):
                problems.append(rel + "：JSON 末尾缺少换行，推送后 blob 哈希会对不上")
            else:
                try:
                    json.loads(data)
                except ValueError:
                    problems.append(rel + "：JSON 无法解析")
        if rel.startswith("book/chapters/"):
            marker = p.stem.split("_", 1)[-1]
            if len(marker) == 64 and hashlib.sha256(data).hexdigest() != marker:
                problems.append(rel + "：冻结正文内容与文件名中的 SHA256 不符")
    for rel, sha, size in rows:
        print(f"{sha}  {size:>8}  {rel}")
    if problems:
        for item in problems:
            print("未通过：" + item, file=sys.stderr)
        sys.exit(1)
    print(f"自检通过：{len(rows)} 个文件。推送后按上表与远端目录回读逐一比对。")


if __name__ == "__main__":
    main()
