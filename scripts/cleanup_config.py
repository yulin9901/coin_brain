#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
配置文件清理工具
自动清理重复和过时的配置项
"""
import os
import sys
import re
import shutil
from datetime import datetime

# 确保app目录在Python路径中
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

CONFIG_PATH = os.path.join(APP_DIR, 'config', 'config.py')
BACKUP_PATH = os.path.join(APP_DIR, 'config', f'config.py.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}')

def backup_config():
    """备份当前配置文件"""
    if os.path.exists(CONFIG_PATH):
        shutil.copy2(CONFIG_PATH, BACKUP_PATH)
        print(f"✅ 配置文件已备份到: {BACKUP_PATH}")
        return True
    else:
        print("❌ 配置文件不存在，无需备份")
        return False

def read_config_file():
    """读取配置文件内容"""
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"❌ 读取配置文件失败: {e}")
        return None

def write_config_file(content):
    """写入配置文件内容"""
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ 配置文件已更新")
        return True
    except Exception as e:
        print(f"❌ 写入配置文件失败: {e}")
        return False

def remove_binance_trading_pairs(content):
    """移除 BINANCE_TRADING_PAIRS 配置"""
    # 查找 BINANCE_TRADING_PAIRS 配置
    pattern = r'BINANCE_TRADING_PAIRS\s*=\s*\[.*?\]'
    
    if re.search(pattern, content, re.DOTALL):
        print("🔍 发现 BINANCE_TRADING_PAIRS 配置")
        
        # 移除该配置
        content = re.sub(pattern, '', content, flags=re.DOTALL)
        
        # 清理多余的空行
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        
        print("✅ 已移除 BINANCE_TRADING_PAIRS 配置")
        return content, True
    else:
        print("ℹ️  未发现 BINANCE_TRADING_PAIRS 配置")
        return content, False

def remove_duplicate_comments(content):
    """移除重复的注释"""
    lines = content.split('\n')
    cleaned_lines = []
    prev_comment = None
    
    for line in lines:
        stripped = line.strip()
        
        # 如果是注释行
        if stripped.startswith('#'):
            # 检查是否与前一个注释重复
            if stripped != prev_comment:
                cleaned_lines.append(line)
                prev_comment = stripped
        else:
            cleaned_lines.append(line)
            prev_comment = None
    
    return '\n'.join(cleaned_lines)

def clean_empty_lines(content):
    """清理多余的空行"""
    # 移除连续的空行，最多保留两个连续空行
    content = re.sub(r'\n\s*\n\s*\n\s*\n+', '\n\n\n', content)
    return content

def validate_trading_pairs_config(content):
    """验证 TRADING_PAIRS 配置是否存在"""
    if 'TRADING_PAIRS' not in content:
        print("⚠️  警告: 未找到 TRADING_PAIRS 配置")
        return False
    
    # 检查是否为空列表
    pattern = r'TRADING_PAIRS\s*=\s*\[\s*\]'
    if re.search(pattern, content):
        print("⚠️  警告: TRADING_PAIRS 配置为空")
        return False
    
    print("✅ TRADING_PAIRS 配置正常")
    return True

def add_migration_comment(content):
    """添加迁移说明注释"""
    migration_comment = """
# 配置迁移说明:
# - 已移除重复的 BINANCE_TRADING_PAIRS 配置
# - 统一使用 TRADING_PAIRS 配置交易对
# - 迁移时间: {}

""".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    # 在文件开头添加注释（在第一个import或配置之前）
    lines = content.split('\n')
    insert_index = 0
    
    # 找到第一个非注释、非空行的位置
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith('#'):
            insert_index = i
            break
    
    lines.insert(insert_index, migration_comment)
    return '\n'.join(lines)

def cleanup_config():
    """清理配置文件"""
    print("配置文件清理工具")
    print("=" * 50)
    
    # 检查配置文件是否存在
    if not os.path.exists(CONFIG_PATH):
        print("❌ 配置文件不存在，请先创建配置文件")
        return False
    
    # 备份配置文件
    if not backup_config():
        return False
    
    # 读取配置文件
    content = read_config_file()
    if content is None:
        return False
    
    print("\n开始清理配置文件...")
    
    # 记录是否有修改
    modified = False
    
    # 1. 移除 BINANCE_TRADING_PAIRS
    content, removed = remove_binance_trading_pairs(content)
    if removed:
        modified = True
    
    # 2. 移除重复注释
    original_content = content
    content = remove_duplicate_comments(content)
    if content != original_content:
        print("✅ 已清理重复注释")
        modified = True
    
    # 3. 清理多余空行
    original_content = content
    content = clean_empty_lines(content)
    if content != original_content:
        print("✅ 已清理多余空行")
        modified = True
    
    # 4. 验证配置
    validate_trading_pairs_config(content)
    
    # 5. 如果有修改，添加迁移注释
    if modified:
        content = add_migration_comment(content)
        print("✅ 已添加迁移说明注释")
    
    # 6. 写入文件
    if modified:
        if write_config_file(content):
            print(f"\n✅ 配置文件清理完成！")
            print(f"   备份文件: {BACKUP_PATH}")
            print(f"   如有问题，可以从备份文件恢复")
        else:
            print("\n❌ 配置文件写入失败")
            return False
    else:
        print("\nℹ️  配置文件无需清理")
        # 删除不必要的备份文件
        if os.path.exists(BACKUP_PATH):
            os.remove(BACKUP_PATH)
            print("   已删除不必要的备份文件")
    
    return True

def restore_config():
    """从备份恢复配置文件"""
    print("配置文件恢复工具")
    print("=" * 50)
    
    # 查找备份文件
    config_dir = os.path.dirname(CONFIG_PATH)
    backup_files = []
    
    for filename in os.listdir(config_dir):
        if filename.startswith('config.py.backup.'):
            backup_files.append(filename)
    
    if not backup_files:
        print("❌ 未找到备份文件")
        return False
    
    # 按时间排序，最新的在前
    backup_files.sort(reverse=True)
    
    print("找到以下备份文件:")
    for i, backup_file in enumerate(backup_files, 1):
        print(f"   {i}. {backup_file}")
    
    try:
        choice = input(f"\n请选择要恢复的备份文件 (1-{len(backup_files)}, 回车选择最新): ").strip()
        
        if not choice:
            choice = 1
        else:
            choice = int(choice)
        
        if 1 <= choice <= len(backup_files):
            backup_file = backup_files[choice - 1]
            backup_path = os.path.join(config_dir, backup_file)
            
            # 恢复文件
            shutil.copy2(backup_path, CONFIG_PATH)
            print(f"✅ 已从 {backup_file} 恢复配置文件")
            return True
        else:
            print("❌ 无效的选择")
            return False
            
    except (ValueError, KeyboardInterrupt):
        print("❌ 操作已取消")
        return False

def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] == '--restore':
        restore_config()
    else:
        cleanup_config()

if __name__ == "__main__":
    main()
