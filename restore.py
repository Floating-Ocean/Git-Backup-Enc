#!/usr/bin/env python3
"""
Git-Backup-Enc: Restore Script
Clones repository, decrypts files/filenames/folders, and restores to original location
"""

import os
import sys
import yaml
import base64
import json
import shutil
from pathlib import Path
from typing import Dict
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding, hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from git import Repo, GitCommandError


class BackupDecryptor:
    """Handles decryption of files and filenames using AES"""
    
    def __init__(self, password: str):
        """Initialize with password"""
        # Use PBKDF2 to derive a 32-byte key from password
        # Must use same salt as BackupEncryptor for compatibility
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
    
    def decrypt_data(self, encrypted_data: bytes) -> bytes:
        """Decrypt data using AES-256-CBC"""
        # Extract IV (first 16 bytes)
        iv = encrypted_data[:16]
        encrypted = encrypted_data[16:]
        
        # Decrypt
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=self.backend)
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(encrypted) + decryptor.finalize()
        
        # Unpad data
        unpadder = padding.PKCS7(128).unpadder()
        data = unpadder.update(padded_data) + unpadder.finalize()
        
        return data
    
    def decrypt_filename(self, encrypted_filename: str) -> str:
        """Decrypt base64url-encoded filename"""
        # Add padding if needed
        padding_needed = (4 - len(encrypted_filename) % 4) % 4
        encrypted_filename += '=' * padding_needed
        
        # Decode from base64url
        encrypted_data = base64.urlsafe_b64decode(encrypted_filename.encode('ascii'))
        
        # Decrypt
        decrypted = self.decrypt_data(encrypted_data)
        return decrypted.decode('utf-8')
    
    def decrypt_file(self, input_path: str, output_path: str):
        """Decrypt file contents"""
        with open(input_path, 'rb') as f:
            encrypted_data = f.read()
        
        decrypted = self.decrypt_data(encrypted_data)
        
        # Create parent directories if needed
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'wb') as f:
            f.write(decrypted)


class GitRestore:
    """Handles git operations for restore"""
    
    def __init__(self, backup_dir: str, git_repo: str, git_branch: str = "main"):
        """Initialize git restore"""
        self.backup_dir = Path(backup_dir).resolve()
        self.git_repo = git_repo
        self.git_branch = git_branch
        self.repo = None
    
    def clone_or_pull(self):
        """Clone repository or pull latest changes"""
        if self.backup_dir.exists() and (self.backup_dir / '.git').exists():
            # Repository already exists, pull latest
            self.repo = Repo(self.backup_dir)
            print(f"Repository exists at {self.backup_dir}")
            
            # Try to pull if remote is configured
            if self.git_repo:
                try:
                    # Check if remote exists
                    if 'origin' in [remote.name for remote in self.repo.remotes]:
                        origin = self.repo.remote('origin')
                        origin.pull(self.git_branch)
                        print("Pulled latest changes from remote")
                    else:
                        print("No remote configured, using local version")
                except (GitCommandError, ValueError) as e:
                    print(f"Warning: Could not pull from remote: {e}")
                    print("Using local version")
            else:
                print("Using local repository (no remote configured)")
        else:
            # Clone repository
            if not self.git_repo:
                raise ValueError("Git repository URL is required for cloning")
            
            print(f"Cloning repository from {self.git_repo}...")
            self.repo = Repo.clone_from(
                self.git_repo,
                self.backup_dir,
                branch=self.git_branch
            )
            print(f"Cloned to {self.backup_dir}")


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


def restore(config_path: str = "config.yaml", restore_dir: str = None):
    """Main restore function"""
    print("=" * 60)
    print("Git-Backup-Enc: Starting restore process")
    print("=" * 60)
    
    # Load configuration
    config = load_config(config_path)
    
    # Override restore directory if provided
    if restore_dir:
        config['restore_dir'] = restore_dir
    
    restore_path = Path(config.get('restore_dir', './restored')).resolve()
    
    # Initialize decryptor
    decryptor = BackupDecryptor(config['password'])
    
    # Initialize git restore
    git_restore = GitRestore(
        config['backup_dir'],
        config.get('git_repo', ''),
        config.get('git_branch', 'main')
    )
    
    # Clone or pull repository
    print("\nSyncing with git repository...")
    git_restore.clone_or_pull()
    
    backup_path = Path(config['backup_dir']).resolve()
    
    # Read and decrypt mapping file
    mapping_encrypted_path = backup_path / 'mapping.enc'
    
    if not mapping_encrypted_path.exists():
        print("Error: Mapping file not found in backup directory")
        sys.exit(1)
    
    print("\nReading file mapping...")
    with open(mapping_encrypted_path, 'rb') as f:
        encrypted_mapping = f.read()
    
    mapping_json = decryptor.decrypt_data(encrypted_mapping).decode('utf-8')
    mapping: Dict[str, str] = json.loads(mapping_json)
    
    print(f"Found {len(mapping)} files to restore")
    
    # Create restore directory if it doesn't exist
    restore_path.mkdir(parents=True, exist_ok=True)
    
    # Decrypt and restore each file
    print("\nDecrypting and restoring files...")
    restored_count = 0
    
    for encrypted_rel_path, original_rel_path in mapping.items():
        encrypted_full_path = backup_path / encrypted_rel_path
        restore_full_path = restore_path / original_rel_path
        
        if not encrypted_full_path.exists():
            print(f"  Warning: Encrypted file not found: {encrypted_rel_path}")
            continue
        
        # Decrypt and restore file
        decryptor.decrypt_file(str(encrypted_full_path), str(restore_full_path))
        restored_count += 1
        
        print(f"  Restored: {original_rel_path}")
    
    print(f"\nRestore completed: {restored_count} files decrypted and restored")
    print(f"Files restored to: {restore_path}")
    
    print("\n" + "=" * 60)
    print("Restore process completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Git-Backup-Enc: Restore encrypted backup')
    parser.add_argument('-c', '--config', default='config.yaml',
                       help='Path to configuration file (default: config.yaml)')
    parser.add_argument('-d', '--restore-dir', 
                       help='Directory to restore files to (overrides config)')
    
    args = parser.parse_args()
    
    try:
        restore(args.config, args.restore_dir)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
