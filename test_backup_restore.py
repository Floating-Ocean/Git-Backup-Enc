#!/usr/bin/env python3
"""
Simple test script to verify backup and restore functionality
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

def create_test_files(test_dir):
    """Create sample files for testing"""
    # Create directory structure
    (test_dir / "documents").mkdir(parents=True)
    (test_dir / "config").mkdir(parents=True)
    
    # Create test files
    (test_dir / "documents" / "notes.txt").write_text(
        "This is a test document.\nLine 2: Important data.\n"
    )
    (test_dir / "config" / "settings.json").write_text(
        '{"app": "test", "version": "1.0"}\n'
    )
    (test_dir / "README.md").write_text(
        "# Test Project\nThis is a test.\n"
    )
    
    return ["documents/notes.txt", "config/settings.json", "README.md"]

def verify_files(original_dir, restored_dir, file_list):
    """Verify that restored files match original files"""
    all_match = True
    for file_path in file_list:
        orig_file = original_dir / file_path
        rest_file = restored_dir / file_path
        
        if not rest_file.exists():
            print(f"✗ File not restored: {file_path}")
            all_match = False
            continue
        
        orig_content = orig_file.read_bytes()
        rest_content = rest_file.read_bytes()
        
        if orig_content == rest_content:
            print(f"✓ File matches: {file_path}")
        else:
            print(f"✗ File differs: {file_path}")
            all_match = False
    
    return all_match

def main():
    print("=" * 60)
    print("Git-Backup-Enc: Test Suite")
    print("=" * 60)
    
    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Setup directories
        source_dir = temp_path / "source"
        backup_dir = temp_path / "backup"
        restore_dir = temp_path / "restored"
        
        source_dir.mkdir()
        
        print("\n1. Creating test files...")
        file_list = create_test_files(source_dir)
        print(f"   Created {len(file_list)} test files")
        
        # Create config
        config_path = temp_path / "config.yaml"
        config_path.write_text(f"""
file_list: {temp_path / 'backup_files.txt'}
backup_dir: {backup_dir}
git_repo: 
git_branch: main
password: test_password_123
source_dir: {source_dir}
restore_dir: {restore_dir}
""")
        
        # Create file list
        file_list_path = temp_path / "backup_files.txt"
        file_list_path.write_text("\n".join(file_list))
        
        # Run backup
        print("\n2. Running backup...")
        import backup
        try:
            backup.backup(str(config_path))
            print("   ✓ Backup completed successfully")
        except Exception as e:
            print(f"   ✗ Backup failed: {e}")
            return 1
        
        # Verify encrypted files exist
        print("\n3. Verifying encryption...")
        encrypted_files = list(backup_dir.rglob("*"))
        encrypted_files = [f for f in encrypted_files if f.is_file() and not f.name.startswith('.')]
        
        # Check that filenames are encrypted (not readable)
        readable_names = [f for f in encrypted_files 
                         if any(name in str(f.name) for name in ['notes', 'settings', 'README'])]
        if readable_names:
            print(f"   ✗ Found readable filenames: {readable_names}")
            return 1
        else:
            print(f"   ✓ All filenames encrypted ({len(encrypted_files)} files)")
        
        # Run restore
        print("\n4. Running restore...")
        import restore as restore_module
        try:
            restore_module.restore(str(config_path))
            print("   ✓ Restore completed successfully")
        except Exception as e:
            print(f"   ✗ Restore failed: {e}")
            return 1
        
        # Verify files
        print("\n5. Verifying restored files...")
        if verify_files(source_dir, restore_dir, file_list):
            print("   ✓ All files restored correctly")
        else:
            print("   ✗ Some files don't match")
            return 1
        
        # Test with wrong password
        print("\n6. Testing wrong password...")
        wrong_config = temp_path / "config_wrong.yaml"
        wrong_config.write_text(f"""
file_list: {temp_path / 'backup_files.txt'}
backup_dir: {backup_dir}
git_repo: 
git_branch: main
password: wrong_password
source_dir: {source_dir}
restore_dir: {temp_path / 'restored_wrong'}
""")
        
        try:
            restore_module.restore(str(wrong_config))
            print("   ✗ Restore should have failed with wrong password")
            return 1
        except Exception:
            print("   ✓ Correctly rejected wrong password")
    
    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(main())
