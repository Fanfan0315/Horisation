# Backend/Controller/csvcontroller.py
"""
CSV API 控制器 - 只负责路由和请求处理
业务逻辑已移至 Backend/Functions 模块
"""

from flask import Blueprint, request, jsonify, current_app
import os
from typing import Optional, Tuple, List
import json
import pandas as pd
import re
from pathlib import Path

# 导入核心功能模块
from Backend.Functions.csv_processor import csv_processor
from Backend.Functions.csv_cleaner import csv_cleaner

bp = Blueprint("csv_api", __name__)

# 配置常量
MAX_BYTES = 100 * 1024 * 1024  # 100MB
ALLOWED_EXT = {'.csv', '.xls', '.xlsx'}


def _get_file_and_bytes() -> Tuple[Optional[str], Optional[bytes], Optional[Tuple[str, int]]]:
    """
    从请求中提取文件并验证

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

def _parse_mapping(default_prefix: str, required: bool = False):
    raw = request.form.get('mapping') or request.args.get('mapping')

    if raw is None:
        json_payload = request.get_json(silent=True) or {}
        raw = json_payload.get('mapping')

    if raw in (None, ""):
        if required:
            return None, ('mapping is required', 400)
        return [], None

    if isinstance(raw, str):
        try:
            mapping = json.loads(raw)
        except json.JSONDecodeError:
            return None, ('invalid mapping json', 400)
    else:
        mapping = raw

    if not isinstance(mapping, list):
        return None, ('mapping must be a list', 400)

    final = []
    for idx, item in enumerate(mapping):
        if not isinstance(item, dict):
            return None, ('mapping items must be objects', 400)
        entry = dict(item)
        entry.setdefault('out_file', f"{default_prefix}_{idx + 1}.xlsx")
        final.append(entry)

    return final, None

def _read_diff_frame(data: bytes, filename: str, sep: Optional[str] = None, encoding: Optional[str] = None):
    df = csv_processor.read_file_to_dataframe(
        data,
        filename=filename,
        sep=sep,
        encoding=encoding
    )
    return df.apply(pd.to_numeric, errors='ignore')


# ==================== API 路由 ====================

@bp.post("/api/csv/preview")
def api_preview():
    """
    预览CSV/Excel文件前N行

    Query Parameters:
        n (int): 预览行数，默认5，最大2000
        sep (str): CSV分隔符，可选
        encoding (str): CSV编码，可选

    Returns:
        JSON: {
            'ok': bool,
            'filename': str,
            'columns': list,
            'rows': list[dict]
        }
    """
    filename, data, err = _get_file_and_bytes()
    if err:
        msg, code = err
        return jsonify({'ok': False, 'error': msg}), code

    # 解析参数
    try:
        n = int(request.args.get('n', '5'))
        n = max(1, min(n, 2000))
    except Exception:
        n = 5

    sep = request.args.get('sep')
    encoding = request.args.get('encoding')

    # 调用核心功能
    try:
        payload = csv_processor.get_preview(
            data,
            n=n,
            sep=sep,
            filename=filename,
            encoding=encoding
        )
        return jsonify({'ok': True, 'filename': filename, **payload})
    except ImportError as e:
        return jsonify({'ok': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'ok': False, 'error': f'parse failed: {e}'}), 400


@bp.post("/api/csv/summary")
def api_summary():
    """
    获取CSV/Excel文件概要信息

    Query Parameters:
        sep (str): CSV分隔符，可选
        encoding (str): CSV编码，可选

    Returns:
        JSON: {
            'ok': bool,
            'filename': str,
            'summary': {
                'rows': int,
                'cols': int,
                'columns': list,
                'dtypes': dict,
                'na_count': dict,
                'na_ratio': dict
            }
        }
    """
    filename, data, err = _get_file_and_bytes()
    if err:
        msg, code = err
        return jsonify({'ok': False, 'error': msg}), code

    sep = request.args.get('sep')
    encoding = request.args.get('encoding')

    try:
        summary = csv_processor.get_summary(
            data,
            sep=sep,
            filename=filename,
            encoding=encoding
        )
        return jsonify({'ok': True, 'filename': filename, 'summary': summary})
    except ImportError as e:
        return jsonify({'ok': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'ok': False, 'error': f'parse failed: {e}'}), 400


@bp.post("/api/csv/clean")
def api_clean():
    """
    清洗CSV数据

    Query Parameters:
        case (str): 列名大小写 ('upper', 'lower', 'title')
        strip_special (bool): 去除特殊字符
        remove_duplicates (bool): 去除重复行

    Returns:
        JSON: {
            'ok': bool,
            'filename': str,
            'cleaned_rows': int,
            'removed_duplicates': int
        }
    """
    filename, data, err = _get_file_and_bytes()
    if err:
        msg, code = err
        return jsonify({'ok': False, 'error': msg}), code

    # 解析参数
    case = request.args.get('case', 'upper')
    strip_special = request.args.get('strip_special', 'true').lower() == 'true'
    remove_dups = request.args.get('remove_duplicates', 'false').lower() == 'true'

    try:
        # 读取数据
        from Backend.Functions.csv_processor import csv_processor
        df = csv_processor.read_file_to_dataframe(data, filename=filename)
        original_rows = len(df)

        # 清洗列名
        df = csv_cleaner.clean_column_name(df, case=case, strip_special=strip_special)

        # 清洗单元格
        df = csv_cleaner.clean_cell_values(df)

        # 去重
        if remove_dups:
            df = csv_cleaner.remove_duplicates(df)

        removed = original_rows - len(df)

        return jsonify({
            'ok': True,
            'filename': filename,
            'cleaned_rows': len(df),
            'removed_duplicates': removed,
            'columns': list(df.columns)
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': f'clean failed: {e}'}), 400


@bp.post("/api/csv/format")
def api_format():
    filename, data, err = _get_file_and_bytes()
    if err:
        msg, code = err
        return jsonify({'ok': False, 'error': msg}), code

    mapping, err = _parse_mapping(Path(filename).stem if filename else 'formatted')
    if err:
        msg, code = err
        return jsonify({'ok': False, 'error': msg}), code

    sep = request.args.get('sep') or request.form.get('sep')
    encoding = request.args.get('encoding') or request.form.get('encoding')

    try:
        df = csv_processor.read_file_to_dataframe(
            data,
            filename=filename,
            sep=sep,
            encoding=encoding
        )

        if mapping:
            df = csv_cleaner.formatting(df, mapping)

        preview = df.head(min(len(df), 500))

        return jsonify({
            'ok': True,
            'filename': filename,
            'total_rows': int(len(df)),
            'columns': list(df.columns),
            'rows': preview.to_dict(orient='records')
        })
    except ImportError as e:
        return jsonify({'ok': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'ok': False, 'error': f'format failed: {e}'}), 400


@bp.post("/api/csv/diff_highlight")
def api_diff_highlight():
    file1 = request.files.get('file1')
    file2 = request.files.get('file2')

    if not file1 or not file1.filename:
        return jsonify({'ok': False, 'error': 'file1 is required'}), 400
    if not file2 or not file2.filename:
        return jsonify({'ok': False, 'error': 'file2 is required'}), 400

    mapping, err = _parse_mapping('diff_highlight', required=True)
    if err:
        msg, code = err
        return jsonify({'ok': False, 'error': msg}), code

    sep1 = request.args.get('sep1') or request.form.get('sep1')
    sep2 = request.args.get('sep2') or request.form.get('sep2')
    encoding1 = request.args.get('encoding1') or request.form.get('encoding1')
    encoding2 = request.args.get('encoding2') or request.form.get('encoding2')

    try:
        data1 = file1.read()
        data2 = file2.read()

        df1 = _read_diff_frame(data1, file1.filename, sep=sep1, encoding=encoding1)
        df2 = _read_diff_frame(data2, file2.filename, sep=sep2, encoding=encoding2)

        if df1.shape != df2.shape:
            return jsonify({'ok': False, 'error': 'files must have the same shape'}), 400
        if list(df1.columns) != list(df2.columns):
            return jsonify({'ok': False, 'error': 'files must share the same columns'}), 400

        csv_processor.diff_highlight(df1, df2, mapping)

        return jsonify({'ok': True, 'created_files': [m['out_file'] for m in mapping]})
    except ImportError as e:
        return jsonify({'ok': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'ok': False, 'error': f'diff highlight failed: {e}'}), 400


@bp.post("/api/csv/diff_report")
def api_diff_report():
    file1 = request.files.get('file1')
    file2 = request.files.get('file2')

    if not file1 or not file1.filename:
        return jsonify({'ok': False, 'error': 'file1 is required'}), 400
    if not file2 or not file2.filename:
        return jsonify({'ok': False, 'error': 'file2 is required'}), 400

    mapping, err = _parse_mapping('diff_report', required=True)
    if err:
        msg, code = err
        return jsonify({'ok': False, 'error': msg}), code

    sep1 = request.args.get('sep1') or request.form.get('sep1')
    sep2 = request.args.get('sep2') or request.form.get('sep2')
    encoding1 = request.args.get('encoding1') or request.form.get('encoding1')
    encoding2 = request.args.get('encoding2') or request.form.get('encoding2')

    try:
        data1 = file1.read()
        data2 = file2.read()

        df1 = _read_diff_frame(data1, file1.filename, sep=sep1, encoding=encoding1)
        df2 = _read_diff_frame(data2, file2.filename, sep=sep2, encoding=encoding2)

        if df1.shape != df2.shape:
            return jsonify({'ok': False, 'error': 'files must have the same shape'}), 400
        if list(df1.columns) != list(df2.columns):
            return jsonify({'ok': False, 'error': 'files must share the same columns'}), 400

        csv_processor.write_diff_report(df1, df2, mapping)

        return jsonify({'ok': True, 'created_files': [m['out_file'] for m in mapping]})
    except ImportError as e:
        return jsonify({'ok': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'ok': False, 'error': f'diff report failed: {e}'}), 400