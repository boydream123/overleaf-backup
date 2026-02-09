#!/usr/bin/env python3
import os
import json
import requests
from datetime import datetime
from pathlib import Path
import sys

CONFIG_FILE = 'config.json'

def load_config():
    """加载配置文件"""
    if not os.path.exists(CONFIG_FILE):
        print(f"错误: 配置文件不存在: {CONFIG_FILE}")
        sys.exit(1)
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            return config
    except json.JSONDecodeError as e:
        print(f"错误: 配置文件格式错误: {e}")
        sys.exit(1)

def get_backup_config(config):
    """获取备份配置"""
    return config.get('backup', {})

def cleanup_old_backups(backup_dir, keep_last):
    """清理旧的备份文件，只保留最近的 N 个"""
    backup_files = sorted(
        backup_dir.glob('backup_*.zip'),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    
    # 删除超过保留数量的文件
    deleted_count = 0
    for old_file in backup_files[keep_last:]:
        try:
            old_file.unlink()
            print(f"  ✓ 已删除旧备份: {old_file.name}")
            deleted_count += 1
        except Exception as e:
            print(f"  ✗ 删除失败 {old_file.name}: {e}")
    
    return deleted_count

def format_size(size_bytes):
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def download_project(project_id, project_name, backup_config):
    """下载单个项目"""
    print(f"\n{'='*60}")
    print(f"开始备份项目: {project_name}")
    print(f"项目 ID: {project_id}")
    print(f"{'='*60}")
    
    # 创建项目专属备份目录
    project_backup_dir = Path(backup_config['backup_dir']) / project_id
    project_backup_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成带时间戳的文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = project_backup_dir / f'backup_{timestamp}.zip'
    
    # 构建下载 URL
    download_url = f"{backup_config['overleaf_url']}/project/{project_id}/download/zip"
    
    # 设置请求头
    headers = {
        'Cookie': backup_config['cookie'],
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        print(f"正在下载: {download_url}")
        
        # 下载文件
        timeout = backup_config.get('timeout', 300)
        response = requests.get(
            download_url, 
            headers=headers, 
            timeout=timeout, 
            stream=True,
            allow_redirects=True
        )
        response.raise_for_status()
        
        # 检查是否是有效的 ZIP 文件
        content_type = response.headers.get('Content-Type', '')
        if 'application/zip' not in content_type and 'application/octet-stream' not in content_type:
            print(f"✗ 备份失败: 返回的不是 ZIP 文件 (Content-Type: {content_type})")
            print(f"  提示: 可能是 Cookie 已过期，请检查配置")
            return False
        
        # 保存文件
        total_size = 0
        with open(output_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    total_size += len(chunk)
        
        # 检查文件是否成功下载
        if output_file.exists() and output_file.stat().st_size > 0:
            file_size = format_size(output_file.stat().st_size)
            print(f"✓ 备份成功!")
            print(f"  文件: {output_file.name}")
            print(f"  大小: {file_size}")
            print(f"  路径: {output_file.absolute()}")
            
            # 清理旧备份
            keep_last = backup_config.get('keep_last', 5)
            print(f"\n清理旧备份 (保留最近 {keep_last} 个)...")
            deleted = cleanup_old_backups(project_backup_dir, keep_last)
            if deleted > 0:
                print(f"✓ 已清理 {deleted} 个旧备份文件")
            else:
                print(f"✓ 无需清理")
            
            return True
        else:
            print(f"✗ 备份失败: 文件为空")
            output_file.unlink(missing_ok=True)
            return False
            
    except requests.exceptions.Timeout:
        print(f"✗ 备份失败: 请求超时 (超过 {timeout} 秒)")
        output_file.unlink(missing_ok=True)
        return False
    except requests.exceptions.RequestException as e:
        print(f"✗ 备份失败: {str(e)}")
        output_file.unlink(missing_ok=True)
        return False
    except Exception as e:
        print(f"✗ 备份失败: 未知错误 - {str(e)}")
        output_file.unlink(missing_ok=True)
        return False

def main():
    """主函数"""
    print("="*60)
    print("          Overleaf 备份系统 v1.0")
    print("="*60)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 加载配置
    config = load_config()
    backup_config = get_backup_config(config)
    
    # 检查必要配置
    if not backup_config.get('cookie'):
        print("\n错误: 未设置 Cookie，请先在配置文件中设置")
        print("提示: 编辑 config.json，在 backup.cookie 字段填入你的 Cookie")
        sys.exit(1)
    
    if not backup_config.get('overleaf_url'):
        print("\n错误: 未设置 Overleaf URL")
        sys.exit(1)
    
    # 创建备份根目录
    Path(backup_config['backup_dir']).mkdir(parents=True, exist_ok=True)
    print(f"备份目录: {Path(backup_config['backup_dir']).absolute()}")
    
    # 遍历所有启用的项目
    projects = config.get('projects', [])
    enabled_projects = [p for p in projects if p.get('enabled', True)]
    
    if not enabled_projects:
        print("\n没有启用的项目需要备份")
        print("提示: 请在 Web 界面或配置文件中添加项目")
        return
    
    print(f"\n找到 {len(enabled_projects)} 个启用的项目")
    
    # 备份统计
    success_count = 0
    fail_count = 0
    
    for i, project in enumerate(enabled_projects, 1):
        print(f"\n[{i}/{len(enabled_projects)}]", end=' ')
        if download_project(project['id'], project['name'], backup_config):
            success_count += 1
        else:
            fail_count += 1
    
    # 输出统计信息
    print(f"\n{'='*60}")
    print(f"备份完成!")
    print(f"成功: {success_count} 个项目")
    print(f"失败: {fail_count} 个项目")
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    # 如果有失败的，返回非零退出码
    if fail_count > 0:
        sys.exit(1)

if __name__ == '__main__':
    main()