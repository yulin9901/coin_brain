#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
安装Windows服务脚本
用于将股票分析系统安装为Windows服务
"""
import os
import sys
import argparse
import subprocess
import winreg

def create_service(service_name, display_name, description, command):
    """创建Windows服务"""
    print(f"正在创建服务 {service_name}...")
    
    # 使用sc命令创建服务
    create_cmd = f'sc create "{service_name}" binPath= "{command}" DisplayName= "{display_name}" start= auto'
    subprocess.run(create_cmd, shell=True, check=True)
    
    # 设置服务描述
    desc_cmd = f'sc description "{service_name}" "{description}"'
    subprocess.run(desc_cmd, shell=True, check=True)
    
    print(f"服务 {service_name} 创建成功")

def install_service():
    """安装股票分析系统服务"""
    # 获取项目根目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    
    # 获取Python解释器路径
    python_exe = sys.executable
    
    # 构建服务命令
    run_script = os.path.join(project_dir, "run.py")
    command = f'"{python_exe}" "{run_script}" --run scheduler'
    
    # 服务信息
    service_name = "StockAnalyzerService"
    display_name = "股票分析系统服务"
    description = "自动收集股票市场数据并生成分析报告的服务"
    
    # 创建服务
    create_service(service_name, display_name, description, command)
    
    print("\n服务安装完成！")
    print(f"可以使用以下命令启动服务：")
    print(f"  sc start {service_name}")
    print(f"可以使用以下命令停止服务：")
    print(f"  sc stop {service_name}")
    print(f"可以使用以下命令删除服务：")
    print(f"  sc delete {service_name}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="安装股票分析系统Windows服务")
    parser.add_argument("--install", action="store_true", help="安装服务")
    
    args = parser.parse_args()
    
    if args.install:
        install_service()
    else:
        parser.print_help()

if __name__ == "__main__":
    # 检查是否以管理员权限运行
    try:
        # 尝试打开一个需要管理员权限的注册表项
        winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion", 0, winreg.KEY_WRITE)
    except PermissionError:
        print("错误: 此脚本需要管理员权限运行")
        print("请右键点击命令提示符或PowerShell，选择'以管理员身份运行'，然后再次运行此脚本")
        sys.exit(1)
    
    main()
