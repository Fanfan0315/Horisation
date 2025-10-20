"""
CSV数据清洗和转换功能模块
包含列名标准化、数据去重、类型转换等功能
"""

import pandas as pd
import numpy as np
import re
from typing import Optional, Dict, List, Any


class CSVCleaner:
    """CSV数据清洗器"""

    @staticmethod
    def clean_column_names(
            df: pd.DataFrame,
            cols: list[str] | None = None,
            *,
            case: str | None = "upper",
            strip_special: bool = True
    ) -> pd.DataFrame:
        """标准化列名.

        Args:
            df: 待处理的数据框。
            cols: 需要处理的列名列表, ``None`` 表示全部列。
            case: 大小写控制, 支持 ``upper``/``lower``/``title``/``None``。
            strip_special: 是否移除除 ``_`` 以外的特殊字符。

        Returns:
            ``pd.DataFrame``: 列名规范化后的数据框, 返回副本避免原地修改。
        """

        df = df.copy()
        target_cols = set(df.columns if cols is None else cols)
        normalised = []

        for original in df.columns:
            if original not in target_cols:
                normalised.append(original)
                continue

            if not isinstance(original, str):
                normalised.append(original)
                continue

            col = original.strip()
            col = re.sub(r"\s+", "_", col)
            if strip_special:
                col = re.sub(r"[^0-9a-zA-Z_]+", "", col)

            case_value = (case or "").lower()
            if case_value == "upper":
                col = col.upper()
            elif case_value == "lower":
                col = col.lower()
            elif case_value == "title":
                col = "_".join(part.capitalize() for part in col.split("_"))

            normalised.append(col)

        df.columns = normalised
        return df

    @staticmethod
    def clean_column_name(
            df: pd.DataFrame,
            cols: list[str] | None = None,
            **kwargs: Any
    ) -> pd.DataFrame:
        """保持兼容的旧接口, 默认转为大写并替换空格。

        旧的调用方可能会额外传入 ``case``、``strip_special`` 等关键字参数,
        因此这里透传给 ``clean_column_names`` 以避免 ``TypeError``。
        """

        if "case" not in kwargs:
            kwargs["case"] = "upper"

        return CSVCleaner.clean_column_names(df, cols=cols, **kwargs)

    @staticmethod
    def clean_cell_values(
        df: pd.DataFrame,
        strip_whitespace: bool = True,
        normalize_missing: bool = True,
        missing_values: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        清洗单元格数据

        Args:
            df: 原始DataFrame
            strip_whitespace: 去除首尾空格
            normalize_missing: 统一缺失值标记为NaN
            missing_values: 缺失值标识列表

        Returns:
            pd.DataFrame: 数据清洗后的DataFrame
        """
        df = df.copy()

        # 去除空格
        if strip_whitespace:
            obj_cols = df.select_dtypes(include=["object"]).columns
            for col in obj_cols:
                df[col] = df[col].apply(
                    lambda x: x.strip() if isinstance(x, str) else x
                )

        # 统一缺失值
        if normalize_missing:
            if missing_values is None:
                missing_values = ["", "NA", "N/A", "na", "-", "null", "None", "nan"]
            df.replace(missing_values, np.nan, inplace=True)

        return df

    @staticmethod
    def remove_duplicates(
        df: pd.DataFrame,
        subset: Optional[List[str]] = None,
        keep: str = 'first'
    ) -> pd.DataFrame:
        """
        去除重复行

        Args:
            df: 原始DataFrame
            subset: 用于判断重复的列（None表示全部列）
            keep: 保留策略 ('first', 'last', False)

        Returns:
            pd.DataFrame: 去重后的数据
        """
        return df.drop_duplicates(subset=subset, keep=keep).reset_index(drop=True)

    @staticmethod
    def formatting(df: pd.DataFrame, mapping: list[dict]) -> pd.DataFrame:
        for m in mapping:
            cols = m.get('Column', [])
            trans_type = m.get('trans_type', None)

            if trans_type == 'str':
                for col in cols:
                    if col in df.columns:
                        df[col] = df[col].astype(str)
                        df[col] = df[col].str.upper()
                        df[col] = df[col].str.strip()
                        df[col] = df[col].str.replace(" ", "_")

            elif trans_type == 'int':
                for col in cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

            elif trans_type == 'float':
                for col in cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors="coerce").round(4)

            elif trans_type == 'bool':
                for col in cols:
                    if col in df.columns:
                        df[col] = df[col].astype("boolean")

            elif trans_type == 'percent':
                for col in cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors="coerce") * 100
                        df[col] = df[col].round(2)
                        df[col] = df[col].apply(lambda x: f"{x}%" if pd.notna(x) else pd.NA)

            elif trans_type == 'date':
                date_format = m.get("format", "YYYY-MM-DD")

                from dateutil import parser
                def parse_date(val):
                    try:
                        return parser.parse(str(val), dayfirst=False, yearfirst=False)
                    except Exception:
                        return pd.NaT

                for col in cols:
                    if col in df.columns:
                        df[col] = df[col].apply(parse_date)

                        if date_format == "YYYY-MM-DD":
                            df[col] = df[col].dt.strftime("%Y-%m-%d")
                        elif date_format == "DD_MM_YY":
                            df[col] = df[col].dt.strftime("%d-%m-%y")
                        elif date_format == "MM-YY":
                            df[col] = df[col].dt.strftime("%m-%y")

            elif trans_type == "scale":
                factor = m.get("factor", 1)
                operation = m.get("operation", "mul")
                for col in cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors="coerce")  # 转数值
                        if operation == "mul":
                            df[col] = df[col] * factor
                        elif operation == "div":
                            df[col] = df[col] / factor
                        elif operation == "add":
                            df[col] = df[col] + factor
                        elif operation == "sub":
                            df[col] = df[col] - factor


            elif trans_type == 'missing':
                strategy = m.get("strategy", None)
                for col in cols:
                    if col in df.columns:
                        if strategy == "mean":
                            df[col] = df[col].fillna(df[col].mean())
                        elif strategy == "median":
                            df[col] = df[col].fillna(df[col].median())
                        elif strategy == "nan":
                            df[col] = df[col].fillna(pd.NA)

            elif trans_type == "outlier":
                method = m.get("method", "zscore")
                replace = m.get("replace", "nan")
                threshold = m.get("threshold", 3)
                for col in cols:
                    if col in df.columns:
                        series = df[col]
                        if method == "zscore":
                            mean, std = series.mean(), series.std()
                            mask = abs(series - mean) > threshold * std
                        elif method == "iqr":
                            q1, q3 = series.quantile([0.25, 0.75])
                            iqr = q3 - q1
                            mask = (series < q1 - threshold * iqr) | (series > q3 + threshold * iqr)

                        if replace == "mean":
                            df.loc[mask, col] = mean
                        elif replace == "median":
                            df.loc[mask, col] = series.median()
                        elif replace == "nan":
                            df.loc[mask, col] = pd.NA

        df = df.astype(object).where(df.notna(), float("nan"))
        return df

# 全局清洗器实例
csv_cleaner = CSVCleaner()
