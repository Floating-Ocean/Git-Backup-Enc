# Git-Backup-Enc 使用说明

## 简介

Git-Backup-Enc 是一个基于 Git 的加密备份工具，支持：
- 基于文件列表的备份（类似 .gitignore 语法，但用于包含而非排除）
- AES-256 加密文件内容、文件名和文件夹名
- 自动提交和推送到 Git 仓库
- 简单的恢复功能

## 安装

### 依赖要求

- Python 3.7 或更高版本
- Git

### 安装依赖包

```bash
pip install -r requirements.txt
```

## 使用方法

### 1. 配置

复制示例配置文件：

```bash
cp config.yaml.example config.yaml
```

编辑 `config.yaml` 配置文件：

```yaml
# 文件列表路径
file_list: backup_files.txt

# 加密备份存储目录
backup_dir: ./backup_encrypted

# Git 仓库地址
git_repo: https://github.com/yourusername/your-backup-repo.git

# Git 分支
git_branch: main

# 加密密码（重要：请妥善保管！）
# 留空则从环境变量 BACKUP_PASSWORD 读取
password: 

# 源文件目录
source_dir: ./

# 恢复目录
restore_dir: ./restored
```

**安全提示**：建议使用环境变量设置密码：

```bash
export BACKUP_PASSWORD="你的安全密码"
```

### 2. 创建文件列表

复制示例文件列表：

```bash
cp backup_files.txt.example backup_files.txt
```

编辑 `backup_files.txt`，添加需要备份的文件模式：

```
# 需要备份的文件列表
# 语法类似 .gitignore，但用于包含文件

# 示例：
*.txt           # 所有 txt 文件
docs/           # 整个 docs 目录
config.json     # 特定文件
**/*.py         # 所有子目录中的 Python 文件
```

### 3. 执行备份

运行备份脚本：

```bash
python backup.py
```

或指定配置文件：

```bash
python backup.py -c /path/to/config.yaml
```

备份过程：
1. 读取文件列表并查找匹配文件
2. 使用 AES-256 加密文件内容、文件名和文件夹名
3. 保存加密文件到备份目录
4. 提交并推送到 Git 仓库

### 4. 恢复备份

运行恢复脚本：

```bash
python restore.py
```

或指定恢复目录：

```bash
python restore.py -d /path/to/restore/directory
```

恢复过程：
1. 克隆或拉取最新的备份仓库
2. 解密所有文件和文件名
3. 恢复文件到指定目录

## 定时备份

### Linux/Mac（使用 cron）

编辑 crontab：

```bash
crontab -e
```

添加定时任务（例如每天凌晨 2 点备份）：

```
0 2 * * * cd /path/to/Git-Backup-Enc && /usr/bin/python3 backup.py
```

或使用提供的脚本：

```
0 2 * * * /path/to/Git-Backup-Enc/run_backup.sh
```

### Windows（使用任务计划程序）

1. 打开任务计划程序
2. 创建新任务
3. 设置触发器（如每天凌晨 2 点）
4. 设置操作运行：`python.exe` 参数：`C:\path\to\backup.py`

## 工作原理

### 备份流程

1. **文件选择**：使用 pathspec（gitignore 风格的模式）匹配文件
2. **加密**：
   - 使用 SHA-256 从密码派生 AES-256 密钥
   - 使用 AES-256-CBC 加密每个文件内容
   - 分别加密每个文件名和文件夹名
   - 为每次加密操作生成随机 IV
3. **存储**：将加密文件保存到备份目录
4. **映射**：创建加密的映射文件以跟踪原始文件名
5. **Git 同步**：提交并推送到远程仓库

### 恢复流程

1. **克隆/拉取**：从 Git 仓库获取最新备份
2. **解密映射**：读取并解密文件名映射
3. **解密文件**：解密每个文件内容并恢复原始文件名
4. **恢复**：将文件保存到指定的恢复目录

## 安全说明

- 🔑 **密码安全**：永远不要将密码提交到 git。使用环境变量或安全的密钥管理
- 🔐 **加密强度**：工具使用 AES-256-CBC 加密，配合强密码使用是安全的
- 🌐 **Git 仓库**：如果包含敏感数据，请确保 Git 仓库是私有的
- 📝 **映射文件**：加密文件名和原始文件名之间的映射也是加密存储的

## 测试

运行测试套件验证功能：

```bash
python test_backup_restore.py
```

## 故障排除

### "Password not found" 错误

确保在 `config.yaml` 中设置了密码或设置了环境变量：

```bash
export BACKUP_PASSWORD="你的密码"
```

### Git 推送失败

- 检查 Git 凭据是否已配置
- 验证仓库 URL 是否正确
- 确保你有仓库的写权限
- 对于 HTTPS，可能需要配置凭据助手或使用 SSH

### 找不到要备份的文件

- 检查 `backup_files.txt` 中的模式
- 验证配置中的 `source_dir` 指向正确位置
- 确保文件列表文件存在且可读

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件
