# Backend/Controller/csvcontroller.py
from flask import Blueprint, request, jsonify
from io import BytesIO
import pandas as pd
import numpy as np
import os
import re
from typing import Optional, Tuple

bp = Blueprint("csv_api", __name__)

MAX_BYTES = 100 * 1024 * 1024
ALLOWED_EXT = {'.csv', '.xls', '.xlsx'}

# ---- CSV 编码回退读取 ----
_USE_PYARROW = False
try:
    import pyarrow  # noqa: F401

    _USE_PYARROW = True
except Exception:
    _USE_PYARROW = False

# 检查 Excel 引擎依赖
_HAS_OPENPYXL = False
_HAS_XLRD = False
try:
    import openpyxl  # noqa: F401

    _HAS_OPENPYXL = True
except ImportError:
    pass

try:
    import xlrd  # noqa: F401

    _HAS_XLRD = True
except ImportError:
    pass


def _read_csv_with_fallback(
    binary: bytes,
    nrows: Optional[int] = None,
    sep: Optional[str] = None,
    encoding: Optional[str] = None
) -> pd.DataFrame:
    """
    优先尝试 UTF-8（及 UTF-8-SIG），失败则回退至常见本地编码。

    Args:
        binary: CSV 文件的二进制数据
        nrows: 限制读取的行数
        sep: 自定义分隔符
        encoding: 指定编码（如提供则直接使用）

    Returns:
        pd.DataFrame: 解析后的数据框
    """
    base_kwargs = {}
    if nrows is not None:
        base_kwargs["nrows"] = nrows
    if sep is not None:
        base_kwargs["sep"] = sep

    # 如果指定了编码，直接使用
    if encoding:
        bio = BytesIO(binary)
        return pd.read_csv(bio, encoding=encoding, **base_kwargs)

    # UTF-8 编码尝试（优先使用 PyArrow 引擎提升性能）
    utf8_tries = [("utf-8", _USE_PYARROW), ("utf-8-sig", _USE_PYARROW)]
    for enc, use_pa in utf8_tries:
        try:
            bio = BytesIO(binary)
            engine = "pyarrow" if use_pa else "c"
            return pd.read_csv(bio, encoding=enc, engine=engine, **base_kwargs)
        except Exception:
            continue

    # 本地编码回退
    local_fallbacks = ["gbk", "gb2312", "big5", "shift_jis", "cp1252"]
    for enc in local_fallbacks:
        try:
            bio = BytesIO(binary)
            return pd.read_csv(bio, encoding=enc, **base_kwargs)
        except Exception:
            continue

    # 最后兜底：latin1（能处理所有字节序列）
    bio = BytesIO(binary)
    return pd.read_csv(bio, encoding="latin1", **base_kwargs)


# ---- 统一入口：CSV/Excel → DataFrame ----
def _to_df(
    binary: bytes,
    nrows: Optional[int] = None,
    sep: Optional[str] = None,
    filename: Optional[str] = None,
    encoding: Optional[str] = None
) -> pd.DataFrame:
    """
    将二进制数据读成 DataFrame。

    Args:
        binary: 文件的二进制数据
        nrows: 限制读取的行数（仅 CSV）
        sep: CSV 分隔符
        filename: 文件名（用于判断文件类型）
        encoding: CSV 编码

    Returns:
        pd.DataFrame: 解析后的数据框

    Raises:
        ImportError: 缺少必要的 Excel 处理库
    """
    name = (filename or "").lower()

    # Excel 文件处理
    if name.endswith((".xls", ".xlsx")):
        bio = BytesIO(binary)

        # 检查 Excel 依赖
        if name.endswith(".xlsx") and not _HAS_OPENPYXL:
            raise ImportError("处理 .xlsx 文件需要 openpyxl 库，请安装: pip install openpyxl")
        elif name.endswith(".xls") and not _HAS_XLRD:
            raise ImportError("处理 .xls 文件需要 xlrd 库，请安装: pip install xlrd")

        # 使用对应引擎读取 Excel
        try:
            engine = "openpyxl" if name.endswith(".xlsx") else "xlrd"
            df = pd.read_excel(bio, engine=engine)
        except Exception as e:
            # 兜底尝试自动检测引擎
            try:
                df = pd.read_excel(bio)
            except Exception:
                raise e
    else:
        # CSV 文件处理
        df = _read_csv_with_fallback(binary, nrows=nrows, sep=sep, encoding=encoding)

    # 统一转换为字符串类型，避免类型比较错误
    df = df.astype(str)

    return df


# ---- 预览和概要函数 ----
def read_csv_preview(
    binary: bytes,
    n: int = 5,
    sep: Optional[str] = None,
    filename: Optional[str] = None,
    encoding: Optional[str] = None
) -> dict:
    """
    返回前 n 行的预览记录与列名。

    Args:
        binary: 文件的二进制数据
        n: 预览行数（默认 5 行）
        sep: CSV 分隔符
        filename: 文件名
        encoding: CSV 编码

    Returns:
        dict: 包含 'columns' 和 'rows' 的字典
    """
    df = _to_df(binary, nrows=n, sep=sep, filename=filename, encoding=encoding)
    head = df.head(n)
    return {
        'columns': list(head.columns),
        'rows': head.to_dict(orient='records')
    }


def summarize_csv(
    binary: bytes,
    sep: Optional[str] = None,
    filename: Optional[str] = None,
    encoding: Optional[str] = None
) -> dict:
    """
    返回整体概要信息：行/列、字段类型、缺失统计等。

    Args:
        binary: 文件的二进制数据
        sep: CSV 分隔符
        filename: 文件名
        encoding: CSV 编码

    Returns:
        dict: 包含行数、列数、数据类型、缺失值统计等信息
    """
    df = _to_df(binary, sep=sep, filename=filename, encoding=encoding)

    # 定义缺失值标识
    MISSING_VALUES = {'', 'nan', 'None', 'NaN', 'null', 'NULL'}

    # 计算缺失值（空字符串、NaN 等视为缺失）
    na_count = {}
    for col in df.columns:
        is_missing = df[col].isin(MISSING_VALUES) | df[col].isna()
        na_count[col] = int(is_missing.sum())

    total_rows = len(df)
    na_ratio = {k: round(v / total_rows, 4) if total_rows else 0.0 for k, v in na_count.items()}

    # 推断数据类型（基于非空值）
    dtypes = {}
    for col in df.columns:
        # 获取非空值
        non_empty = df[col][~(df[col].isin(MISSING_VALUES) | df[col].isna())]

        if len(non_empty) == 0:
            dtypes[col] = 'unknown'
            continue

        # 取样本值推断类型
        sample = str(non_empty.iloc[0])

        # 检查是否为数字（整数或浮点数）
        if re.match(r'^-?\d+(\.\d+)?$', sample):
            dtypes[col] = 'numeric'
        # 检查是否为日期格式
        elif re.match(r'^\d{4}-\d{2}-\d{2}', sample):
            dtypes[col] = 'date'
        else:
            dtypes[col] = 'text'

    return {
        'rows': int(total_rows),
        'cols': int(df.shape[1]),
        'columns': list(df.columns),
        'dtypes': dtypes,
        'na_count': na_count,
        'na_ratio': na_ratio
    }


# ---- 文件处理函数 ----
def _get_file_and_bytes() -> Tuple[Optional[str], Optional[bytes], Optional[Tuple[str, int]]]:
    """
    从请求中提取文件并验证。

    Returns:
        Tuple: (filename, binary_data, error)
            - filename: 文件名
            - binary_data: 文件的二进制数据
            - error: 错误信息元组 (message, status_code)，无错误时为 None
    """
    if 'file' not in request.files:
        return None, None, ('no file field', 400)

    f = request.files['file']
    if not f or not f.filename or f.filename.strip() == '':
        return None, None, ('empty filename', 400)

    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ALLOWED_EXT:
        return None, None, ('only .csv/.xls/.xlsx allowed', 400)

    # 检查文件大小
    f.seek(0, 2)
    size = f.tell()
    f.seek(0)
    if size > MAX_BYTES:
        return None, None, ('file too large', 413)

    data = f.read()
    return f.filename, data, None


# ---- API 路由 ----
@bp.post("/api/csv/preview")
def api_preview():
    filename, data, err = _get_file_and_bytes()
    if err:
        msg, code = err
        return jsonify({'ok': False, 'error': msg}), code

    try:
        n = int(request.args.get('n', '5'))
        n = max(1, min(n, 2000))
    except Exception:
        n = 5

    # 获取编码和分隔符参数
    sep = request.args.get('sep')
    encoding = request.args.get('encoding')

    try:
        payload = read_csv_preview(data, n=n, sep=sep, filename=filename, encoding=encoding)
        return jsonify({'ok': True, 'filename': filename, **payload})
    except ImportError as e:
        # 处理缺少依赖的情况
        return jsonify({'ok': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'ok': False, 'error': f'parse failed: {e}'}), 400


@bp.post("/api/csv/summary")
def api_summary():
    filename, data, err = _get_file_and_bytes()
    if err:
        msg, code = err
        return jsonify({'ok': False, 'error': msg}), code

    sep = request.args.get('sep')
    encoding = request.args.get('encoding')

    try:
        summary = summarize_csv(data, sep=sep, filename=filename, encoding=encoding)
        return jsonify({'ok': True, 'filename': filename, 'summary': summary})
    except ImportError as e:
        # 处理缺少依赖的情况
        return jsonify({'ok': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'ok': False, 'error': f'parse failed: {e}'}), 400