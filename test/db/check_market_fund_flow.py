#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import akshare as ak
import pandas as pd

def check_market_fund_flow():
    """检查 stock_market_fund_flow 函数返回的数据结构"""
    print("调用 ak.stock_market_fund_flow()...")
    try:
        df = ak.stock_market_fund_flow()
        print(f"返回数据类型: {type(df)}")
        print(f"数据形状: {df.shape}")
        print(f"列名: {df.columns.tolist()}")
        print("\n前5行数据:")
        print(df.head())
        
        # 检查是否有板块名称列
        possible_name_columns = [col for col in df.columns if '名称' in col or 'name' in col.lower() or '板块' in col]
        print(f"\n可能包含板块名称的列: {possible_name_columns}")
        
        # 检查所有列的唯一值数量，帮助识别哪一列可能是板块名称
        print("\n各列的唯一值数量:")
        for col in df.columns:
            unique_values = df[col].nunique()
            print(f"{col}: {unique_values} 个唯一值")
            if unique_values < 10:  # 如果唯一值较少，显示这些值
                print(f"  唯一值: {df[col].unique()}")
    except Exception as e:
        print(f"调用 ak.stock_market_fund_flow() 时出错: {e}")
    
    # 尝试其他可能的函数
    print("\n\n尝试调用 ak.stock_sector_fund_flow_rank()...")
    try:
        df2 = ak.stock_sector_fund_flow_rank()
        print(f"返回数据类型: {type(df2)}")
        print(f"数据形状: {df2.shape}")
        print(f"列名: {df2.columns.tolist()}")
        print("\n前5行数据:")
        print(df2.head())
    except Exception as e:
        print(f"调用 ak.stock_sector_fund_flow_rank() 时出错: {e}")

if __name__ == "__main__":
    check_market_fund_flow()
