# Workspace Rules

## Mandatory Router Configuration Rules: Backup, Change Summary & Chat History

Whenever asked to make, apply, or test any configuration changes on any Keenetic router (via RCI, CLI, or API):

1. **Always run a fresh backup BEFORE making any changes**:
   ```bash
   python3 keenetic.py --host <target_router> backup
   ```
   Verify that the backup completes successfully (actual `startup-config.txt` and `running-config.txt` updated, and older backup preserved in `archive/<timestamp>/`).
2. **Apply the requested changes and verify** that the changes took effect.
3. **Capture post-change backup and save audit records**:
   - **Post-Change Backup**: Run backup to capture the newly updated configuration:
     ```bash
     python3 keenetic.py --host <target_router> backup
     ```
   - **Change Summary (`changes-summary.md`)**:
     Alongside the backup in `backups/<target_router>/`, record a clear summary documenting:
     - **Timestamp & Target Host**
     - **WHY changes were made**: User request, root cause, or operational goal
     - **WHAT changes were made**: Exact RCI endpoints, CLI commands, parameters, and before/after values
     - **Verification & Results**: How the change was validated
   - **Chat History (`chat-history.md` or `transcript.jsonl`)**:
     Save the chat history / conversation transcript leading up to and executing the change in `backups/<target_router>/chat-history.md` (or copy the session transcript `transcript.jsonl`).
4. **Convenience CLI Helper**:
   You can write the files directly, or use the built-in helper:
   ```bash
   python3 keenetic.py --host <target_router> log-change \
     --why "<why changes were made>" \
     --what "<exact commands and changes applied>" \
     --chat "<chat transcript content or path to transcript.jsonl>" \
     --verification "<verification results>"
   ```
   All change summaries and chat histories are kept in `backups/<target_router>/` and automatically preserved in `archive/<timestamp>/` during future backups.
