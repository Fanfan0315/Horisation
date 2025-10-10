from io import BytesIO
import pandas as pd
import numpy as np
from typing import Optional, List, Dict

def _to_df(binary: bytes, encoding: str = 'utf-8') -> pd.DataFrame:
    """
    将二进制 CSV 读成 DataFrame。

    Args:
        binary: CSV 文件的二进制数据
        encoding: 编码格式（默认 UTF-8）

    Returns:
        pd.DataFrame: 解析后的数据框
    """
    bio = BytesIO(binary)
    df = pd.read_csv(bio, encoding=encoding)
    return df

def read_csv_preview(binary: bytes, n: int = 5, encoding: str = 'utf-8') -> Dict:
    """
    返回前 n 行的预览记录与列名。

    Args:
        binary: CSV 文件的二进制数据
        n: 预览行数（默认 5 行）
        encoding: 编码格式

    Returns:
        dict: 包含 'columns' 和 'rows' 的字典
    """
    df = _to_df(binary, encoding=encoding)
    head = df.head(n)
    return {
        'columns': list(head.columns),
        'rows': head.to_dict(orient='records')
    }


def summarize_csv(binary: bytes, encoding: str = 'utf-8') -> Dict:
    """
    返回整体概要信息：行/列、字段类型、缺失统计等。

    Args:
        binary: CSV 文件的二进制数据
        encoding: 编码格式

    Returns:
        dict: 包含行数、列数、数据类型、缺失值统计等信息
    """
    df = _to_df(binary, encoding=encoding)

    # 字段类型（pandas dtype -> 简单字符串）
    dtypes = {col: str(dt) for col, dt in df.dtypes.items()}

    # 缺失值计数与占比
    na_count = df.isna().sum().to_dict()
    total_rows = len(df)
    na_ratio = {k: round(v / total_rows, 4) if total_rows else 0.0 for k, v in na_count.items()}

    return {
        'rows': int(total_rows),
        'cols': int(df.shape[1]),
        'columns': list(df.columns),
        'dtypes': dtypes,
        'na_count': na_count,
        'na_ratio': na_ratio
    }

# Data cleaning
def clean_csv(
    binary: bytes,
    subset: Optional[List[str]] = None,
    keep: str = 'first',
    strip_cell_space: bool = True,
    dedupe_columns: bool = True,
    encoding: str = 'utf-8'
) -> pd.DataFrame:
    """
    清洗 CSV 数据。

    Args:
        binary: CSV 文件的二进制数据
        subset: 用于去重的列名列表
        keep: 保留哪个重复项 ('first', 'last', False)
        strip_cell_space: 是否去除单元格首尾空格
        dedupe_columns: 是否对重复列名去重
        encoding: 编码格式

    Returns:
        pd.DataFrame: 清洗后的数据框
    """
    df = _to_df(binary, encoding=encoding)

    # 列名规范化：转大写 + 去空格 + 去重
    new_cols = []
    seen = {}
    for c in df.columns:
        name = str(c).strip().upper()
        if dedupe_columns:
            count = seen.get(name, 0)
            if count > 0:
                name = f"{name}_{count}"
            seen[name] = count + 1
        new_cols.append(name)
    df.columns = new_cols

    # 去除单元格首尾空格
    if strip_cell_space:
        obj_cols = df.select_dtypes(include=["object"]).columns
        for col in obj_cols:
            df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)

    # 去重
    df = df.drop_duplicates(subset=subset, keep=keep).reset_index(drop=True)

    return df

# DataFrame merge
def concat_dfs(
    dfs: List[pd.DataFrame],
    uppercase_cols: bool = True,
    alias: Optional[Dict[str, str]] = None
) -> pd.DataFrame:
    """
    纵向合并多个 DataFrame：列取并集，缺失列自动补 NaN。

    Args:
        dfs: 要合并的 DataFrame 列表
        uppercase_cols: 是否把列名统一成大写（避免 id vs ID）
        alias: 列名同义映射，如 {'user_id': 'ID', 'uid': 'ID'}

    Returns:
        pd.DataFrame: 合并后的数据框
    """
    normed = []
    for df in dfs:
        df = df.copy()
        if alias:
            df.rename(columns=alias, inplace=True)
        if uppercase_cols:
            df.columns = [str(c).strip().upper() for c in df.columns]
        normed.append(df)

    result = pd.concat(normed, axis=0, ignore_index=True, sort=False)
    return result


# DataFrame Exporting
def export_data(
    df: pd.DataFrame,
    filename: str = 'output.csv',
    file_format: Optional[str] = None
) -> None:
    """
    通用导出函数：支持 CSV, Excel, JSON。

    Args:
        df: 需要导出的 DataFrame
        filename: 文件名（默认 output.csv）
        file_format: 文件格式 ('csv', 'excel', 'json')，默认根据文件扩展名判断

    Raises:
        ValueError: 无法识别文件格式或格式不支持
    """
    # 如果没有指定格式，则从文件名扩展名推断
    if file_format is None:
        lower_filename = filename.lower()
        if lower_filename.endswith('.csv'):
            file_format = 'csv'
        elif lower_filename.endswith(('.xls', '.xlsx')):
            file_format = 'excel'
        elif lower_filename.endswith('.json'):
            file_format = 'json'
        else:
            raise ValueError(
                f"无法识别文件格式：{filename}。请指定 file_format 参数 ('csv', 'excel', 'json')"
            )

    # 根据不同格式导出
    if file_format == 'csv':
        df.to_csv(filename, index=False, encoding='utf-8-sig')
    elif file_format == 'excel':
        df.to_excel(filename, index=False, engine='openpyxl')
    elif file_format == 'json':
        df.to_json(filename, orient='records', force_ascii=False, indent=2)
    else:
        raise ValueError(f"不支持的文件格式: {file_format}")
