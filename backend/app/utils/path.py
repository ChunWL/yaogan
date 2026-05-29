"""
路径管理模块
统一管理项目所有路径，支持从任意子模块定位项目根目录
"""

from pathlib import Path
from typing import Optional

PROJECT_MARKER = "gt_platform"


def find_project_root(start_path: Optional[Path] = None) -> Path:
    """
    从当前位置向上查找项目根目录（通过查找 marker file）

    参数：
        start_path: 起始查找路径，默认为此文件所在目录
        marker_file: marker 文件名

    返回：
        Path: 项目根目录路径

    异常：
        FileNotFoundError: 找不到 marker file
    """
    if start_path is None:
        start_path = Path(__file__).parent

    current = Path(start_path).resolve()

    for parent in [current, *current.parents]:
        if (parent / PROJECT_MARKER).exists():
            return parent

    raise FileNotFoundError(
        f"Could not find '{PROJECT_MARKER}' in {current} or any parent directory"
    )
