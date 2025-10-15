#!/usr/bin/env python3
"""
Git-Backup-Enc: Backup Script
Reads a file list, encrypts files/filenames/folders, and pushes to git
"""

import os
import sys
import yaml
import pathspec
import base64
import json
import shutil
from pathlib import Path
from typing import List, Dict, Set
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding, hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from git import Repo, GitCommandError


class BackupEncryptor:
    """Handles encryption of files and filenames using AES"""
    
    def __init__(self, password: str):
        """Initialize with password"""
        # Use PBKDF2 to derive a 32-byte key from password
        # Using a fixed salt for deterministic key derivation
        # (so same password always produces same key for restore compatibility)
        # In production, consider using a per-backup random salt stored with backup
        salt = b'Git-Backup-Enc-Salt-v1'  # Fixed salt for backward compatibility
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        self.key = kdf.derive(password.encode())
        self.backend = default_backend()
    
    def encrypt_data(self, data: bytes) -> bytes:
        """Encrypt data using AES-256-CBC"""
        # Generate random IV
        iv = os.urandom(16)
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=self.backend)
        encryptor = cipher.encryptor()
        
        # Pad data to block size
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(data) + padder.finalize()
        
        # Encrypt
        encrypted = encryptor.update(padded_data) + encryptor.finalize()
        
        # Return IV + encrypted data
        return iv + encrypted
    
    def encrypt_filename(self, filename: str) -> str:
        """Encrypt filename and return base64url-encoded string"""
        encrypted = self.encrypt_data(filename.encode('utf-8'))
        # Use base64url encoding to make it filesystem-safe
        return base64.urlsafe_b64encode(encrypted).decode('ascii').rstrip('=')
    
    def encrypt_file(self, input_path: str, output_path: str):
        """Encrypt file contents"""
        with open(input_path, 'rb') as f:
            data = f.read()
        
        encrypted = self.encrypt_data(data)
        
        with open(output_path, 'wb') as f:
            f.write(encrypted)


class FileListReader:
    """Reads and processes file list with gitignore-like syntax"""
    
    def __init__(self, file_list_path: str, source_dir: str):
        """Initialize with file list path and source directory"""
        self.file_list_path = file_list_path
        self.source_dir = Path(source_dir).resolve()
        self.patterns = []
        
    def read_patterns(self):
        """Read patterns from file list"""
        if not os.path.exists(self.file_list_path):
            raise FileNotFoundError(f"File list not found: {self.file_list_path}")
        
        with open(self.file_list_path, 'r') as f:
            lines = f.readlines()
        
        # Filter out comments and empty lines
        self.patterns = [line.strip() for line in lines 
                        if line.strip() and not line.strip().startswith('#')]
    
    def get_matching_files(self) -> Set[Path]:
        """Get all files matching the patterns"""
        if not self.patterns:
            self.read_patterns()
        
        # Create pathspec from patterns
        spec = pathspec.PathSpec.from_lines('gitwildmatch', self.patterns)
        
        matching_files = set()
        
        # Walk through source directory
        for root, dirs, files in os.walk(self.source_dir):
            root_path = Path(root)
            
            # Get relative path from source_dir
            try:
                rel_root = root_path.relative_to(self.source_dir)
            except ValueError:
                continue
            
            # Check each file
            for file in files:
                file_path = root_path / file
                rel_path = file_path.relative_to(self.source_dir)
                
                # Convert to posix path for matching
                posix_path = rel_path.as_posix()
                
                if spec.match_file(posix_path):
                    matching_files.add(file_path)
        
        return matching_files


class GitBackup:
    """Handles git operations for backup"""
    
    def __init__(self, backup_dir: str, git_repo: str, git_branch: str = "main"):
        """Initialize git backup"""
        self.backup_dir = Path(backup_dir).resolve()
        self.git_repo = git_repo
        self.git_branch = git_branch
        self.repo = None
    
    def init_repo(self):
        """Initialize or clone git repository"""
        if self.backup_dir.exists() and (self.backup_dir / '.git').exists():
            # Repository already exists
            self.repo = Repo(self.backup_dir)
            print(f"Using existing repository at {self.backup_dir}")
        else:
            # Create directory if it doesn't exist
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Initialize new repo
            self.repo = Repo.init(self.backup_dir)
            print(f"Initialized new repository at {self.backup_dir}")
            
            # Add remote if provided
            if self.git_repo:
                try:
                    self.repo.create_remote('origin', self.git_repo)
                except GitCommandError:
                    # Remote might already exist
                    pass
    
    def commit_and_push(self, commit_message: str = "Backup update"):
        """Commit all changes and push to remote"""
        if not self.repo:
            raise RuntimeError("Repository not initialized")
        
        # Add all files
        self.repo.git.add(A=True)
        
        # Check if there are changes to commit
        if self.repo.is_dirty() or self.repo.untracked_files:
            self.repo.index.commit(commit_message)
            print(f"Committed changes: {commit_message}")
        else:
            print("No changes to commit")
        
        # Push to remote if configured
        if self.git_repo:
            try:
                origin = self.repo.remote('origin')
                origin.push(self.git_branch)
                print(f"Pushed to {self.git_repo}")
            except GitCommandError as e:
                print(f"Warning: Could not push to remote: {e}")
                print("You may need to configure git credentials or push manually")


def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file"""
    if not os.path.exists(config_path):
        print(f"Error: Configuration file not found: {config_path}")
        sys.exit(1)
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Get password from environment if not in config
    if not config.get('password'):
        config['password'] = os.environ.get('BACKUP_PASSWORD')
        if not config['password']:
            print("Error: Password not found in config or BACKUP_PASSWORD environment variable")
            sys.exit(1)
    
    return config


def backup(config_path: str = "config.yaml"):
    """Main backup function"""
    print("=" * 60)
    print("Git-Backup-Enc: Starting backup process")
    print("=" * 60)
    
    # Load configuration
    config = load_config(config_path)
    
    # Initialize encryptor
    encryptor = BackupEncryptor(config['password'])
    
    # Read file list
    file_reader = FileListReader(
        config['file_list'],
        config.get('source_dir', './')
    )
    
    # Get matching files
    print("\nScanning for files to backup...")
    matching_files = file_reader.get_matching_files()
    print(f"Found {len(matching_files)} files to backup")
    
    if not matching_files:
        print("No files found to backup. Exiting.")
        return
    
    # Initialize git backup
    git_backup = GitBackup(
        config['backup_dir'],
        config.get('git_repo', ''),
        config.get('git_branch', 'main')
    )
    git_backup.init_repo()
    
    # Create mapping file to track encrypted names
    mapping = {}
    
    # Clear backup directory (except .git)
    backup_path = Path(config['backup_dir'])
    for item in backup_path.iterdir():
        if item.name != '.git':
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
    
    # Process each file
    print("\nEncrypting and copying files...")
    source_dir = Path(config.get('source_dir', './')).resolve()
    
    for file_path in matching_files:
        # Get relative path from source directory
        rel_path = file_path.relative_to(source_dir)
        
        # Encrypt directory structure and filename
        parts = list(rel_path.parts)
        encrypted_parts = [encryptor.encrypt_filename(part) for part in parts]
        
        # Create encrypted path
        encrypted_rel_path = Path(*encrypted_parts)
        encrypted_full_path = backup_path / encrypted_rel_path
        
        # Create encrypted directory structure
        encrypted_full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Encrypt and copy file
        encryptor.encrypt_file(str(file_path), str(encrypted_full_path))
        
        # Store mapping
        mapping[str(encrypted_rel_path)] = str(rel_path)
        
        print(f"  Encrypted: {rel_path}")
    
    # Save mapping file (encrypted)
    mapping_json = json.dumps(mapping, indent=2)
    mapping_encrypted_path = backup_path / 'mapping.enc'
    with open(mapping_encrypted_path, 'wb') as f:
        f.write(encryptor.encrypt_data(mapping_json.encode('utf-8')))
    
    print(f"\nBackup completed: {len(matching_files)} files encrypted")
    
    # Commit and push
    print("\nCommitting to git...")
    from datetime import datetime
    commit_msg = f"Backup: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    git_backup.commit_and_push(commit_msg)
    
    print("\n" + "=" * 60)
    print("Backup process completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Git-Backup-Enc: Backup files with encryption')
    parser.add_argument('-c', '--config', default='config.yaml',
                       help='Path to configuration file (default: config.yaml)')
    
    args = parser.parse_args()
    
    try:
        backup(args.config)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
