# Git-Backup-Enc
A tool to upload data via git regularly, with simple encryptions.

基于 Git 的定时备份工具，支持 AES 加密文件内容、文件名和文件夹名。

Code built using vibe coding (ai), use at your own risk.

代码使用 AI 编写，自测可用但不保证可用性。

## Features / 功能特点

- 📁 File list-based backup (支持基于文件列表的备份)
- 🔐 AES-256 encryption for file contents, filenames, and folder names (AES-256 加密文件内容、文件名和文件夹名)
- 🌲 Git integration for version control and remote storage (集成 Git 进行版本控制和远程存储)
- 🔄 Easy restore functionality (便捷的恢复功能)
- 📝 Gitignore-like syntax for file selection (类似 .gitignore 的文件选择语法)

## Installation / 安装

### Prerequisites / 前置要求

- Python 3.7 or higher
- Git

### Install Dependencies / 安装依赖

```bash
pip install -r requirements.txt
```

## Usage / 使用方法

### 1. Configuration / 配置

Copy the example configuration file:

```bash
cp config.yaml.example config.yaml
```

Edit `config.yaml` with your settings:

```yaml
# Path to the file containing list of files to backup
file_list: backup_files.txt

# Directory where encrypted backup will be stored
backup_dir: ./backup_encrypted

# Git repository URL for backup
git_repo: https://github.com/yourusername/your-backup-repo.git

# Branch name for backup
git_branch: main

# Encryption password (IMPORTANT: Keep this secure!)
# Leave empty to read from environment variable BACKUP_PASSWORD
password: 

# Source directory (where your files to backup are located)
source_dir: ./

# Restore directory (where files will be restored to)
restore_dir: ./restored
```

**Important / 重要**: For security, it's recommended to use environment variables for the password:

```bash
export BACKUP_PASSWORD="your-secure-password"
```

### 2. Create File List / 创建文件列表

Create or copy the example file list:

```bash
cp backup_files.txt.example backup_files.txt
```

Edit `backup_files.txt` with patterns of files you want to backup:

```
# List of files and directories to backup
# Syntax similar to .gitignore but for inclusion

# Examples:
*.txt           # all .txt files
docs/           # entire docs directory
config.json     # specific file
**/*.py         # all Python files in any subdirectory
```

### 3. Backup / 备份

**Manual Backup**:

Run the backup script:

```bash
python3 backup.py
```

Or with a custom config file:

```bash
python3 backup.py -c /path/to/config.yaml
```

**Automatic Scheduled Backups**:

For cross-platform automatic backups, use the scheduler:

```bash
# Run with default 24-hour interval
python3 scheduler.py

# Run every 12 hours
python3 scheduler.py --interval 12

# Run every 30 minutes
python3 scheduler.py --interval 0.5

# With custom config
python3 scheduler.py -c /path/to/config.yaml --interval 6
```

The scheduler will:
- Run an immediate backup when started
- Automatically run backups at the specified interval
- Continue running until stopped (Ctrl+C)
- Work cross-platform (Windows, Linux, Mac)

The backup process:
1. Read the file list and find matching files
2. Encrypt file contents, filenames, and folder names using AES-256
3. Save encrypted files to `content.enc/` subdirectory
4. Commit and push to the configured git repository (only if there are changes)

### 4. Restore / 恢复

Run the restore script:

```bash
python3 restore.py
```

Or with a custom restore directory:

```bash
python restore.py -d /path/to/restore/directory
```

The script will:
1. Clone or pull the latest backup from the git repository
2. Decrypt all files and filenames
3. Restore files to the specified directory

## Scheduling / 定时任务

### Recommended: Use Built-in Scheduler (Cross-platform)

The easiest way to schedule automatic backups is to use the included scheduler script:

```bash
# Run scheduler with default 24-hour interval
python3 scheduler.py

# Run every 6 hours
python3 scheduler.py --interval 6

# Run every 30 minutes
python3 scheduler.py --interval 0.5
```

The scheduler can run as:
- **Windows**: Background service or startup task
- **Linux/Mac**: Background process or systemd service

To run the scheduler in the background:

**Linux/Mac**:
```bash
nohup python3 scheduler.py --interval 24 > scheduler.log 2>&1 &
```

**Windows** (PowerShell):
```powershell
Start-Process python3 -ArgumentList "scheduler.py --interval 24" -WindowStyle Hidden
```

### Alternative: System Schedulers

If you prefer using system schedulers instead:

### Linux/Mac (using cron)

Edit crontab:

```bash
crontab -e
```

Add a line for daily backup at 2 AM:

```
0 2 * * * cd /path/to/Git-Backup-Enc && /usr/bin/python3 backup.py
```

### Windows (using Task Scheduler)

1. Open Task Scheduler
2. Create a new task
3. Set trigger (e.g., daily at 2 AM)
4. Set action to run: `python.exe` with argument: `C:\path\to\backup.py`

## Security Considerations / 安全注意事项

- 🔑 **Password Security**: Never commit your password to git. Use environment variables or secure key management.
- 🔐 **Encryption**: The tool uses AES-256-CBC encryption with PBKDF2-HMAC-SHA256 key derivation (100,000 iterations), which is secure when used with a strong password.
- 🌐 **Git Repository**: Make sure your git repository is private if it contains sensitive data.
- 📝 **Mapping File**: The mapping between encrypted and original filenames is stored encrypted in the backup.
- 📏 **Filename Hashing**: Each file's entire relative path is hashed to a single 64-character name using HMAC-SHA256, creating a flat backup structure with no path length issues.

## File Structure / 文件结构

```
Git-Backup-Enc/
├── backup.py              # Manual backup script
├── restore.py             # Restore script
├── scheduler.py           # Automatic backup scheduler (NEW)
├── config.yaml            # Configuration file
├── backup_files.txt       # File list for backup
├── requirements.txt       # Python dependencies
└── README.md             # This file

Backup Repository Structure:
backup_encrypted/
├── .git/                  # Git repository
├── content.enc/           # Encrypted files (NEW)
│   ├── abc123...def       # Encrypted file 1
│   ├── 456789...ghi       # Encrypted file 2
│   └── xyz789...123       # Encrypted file 3
└── mapping.enc            # Encrypted filename mapping
```

## How It Works / 工作原理

### Backup Process / 备份过程

1. **File Selection**: Uses pathspec (gitignore-style patterns) to match files
2. **Encryption**: 
   - Derives AES-256 key from password using PBKDF2-HMAC-SHA256 (100,000 iterations)
   - Encrypts each file content with AES-256-CBC using deterministic IV (derived from content)
   - Hashes entire relative path using HMAC-SHA256 to create a single 64-character filename
   - Deterministic encryption ensures unchanged files produce identical output (efficient git)
3. **Storage**: Saves encrypted files in `content.enc/` subdirectory (organized structure)
4. **Cleanup**: Clears backup directory before saving to remove old/deleted files
5. **Mapping**: Creates encrypted mapping file to track original filenames and paths
6. **Git Sync**: Commits and pushes to remote repository (only changed files are uploaded)

### Restore Process / 恢复过程

1. **Clone/Pull**: Gets latest backup from git repository
2. **Decrypt Mapping**: Reads and decrypts the filename mapping
3. **Decrypt Files**: Decrypts each file content and restores original filenames
4. **Restore**: Saves files to specified restore directory

## Example / 示例

### Backup Example

```bash
$ python backup.py
============================================================
Git-Backup-Enc: Starting backup process
============================================================

Scanning for files to backup...
Found 5 files to backup

Encrypting and copying files...
  Encrypted: documents/notes.txt
  Encrypted: config/settings.json
  Encrypted: scripts/deploy.sh
  Encrypted: data/database.db
  Encrypted: README.md

Backup completed: 5 files encrypted

Committing to git...
Committed changes: Backup: 2025-10-15 13:45:00
Pushed to https://github.com/yourusername/your-backup-repo.git

============================================================
Backup process completed successfully!
============================================================
```

### Restore Example

```bash
$ python restore.py
============================================================
Git-Backup-Enc: Starting restore process
============================================================

Syncing with git repository...
Pulled latest changes

Reading file mapping...
Found 5 files to restore

Decrypting and restoring files...
  Restored: documents/notes.txt
  Restored: config/settings.json
  Restored: scripts/deploy.sh
  Restored: data/database.db
  Restored: README.md

Restore completed: 5 files decrypted and restored
Files restored to: /home/user/restored

============================================================
Restore process completed successfully!
============================================================
```

## Troubleshooting / 故障排除

### "Password not found" error

Make sure to set the password either in `config.yaml` or as an environment variable:

```bash
export BACKUP_PASSWORD="your-password"
```

### Git push fails

- Check git credentials are configured
- Verify repository URL is correct
- Ensure you have write access to the repository
- For HTTPS, you may need to configure credential helper or use SSH

### No files found to backup

- Check the patterns in `backup_files.txt`
- Verify `source_dir` in config points to correct location
- Make sure file list file exists and is readable

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

