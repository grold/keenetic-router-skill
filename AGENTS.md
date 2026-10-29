# Workspace Rules

## Mandatory Pre-Change Router Backup

Whenever asked to make, apply, or test any configuration changes on any Keenetic router (via RCI, CLI, or API):
1. **Always run a fresh backup BEFORE making any changes**:
   ```bash
   python3 keenetic.py --host <target_router> backup
   ```
2. Verify that the backup completes successfully (actual `startup-config.txt` and `running-config.txt` updated, and older backup preserved in `archive/<timestamp>/`).
3. Only after the fresh backup is confirmed, proceed with applying the requested changes.
