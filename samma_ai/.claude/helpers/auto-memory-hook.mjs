/**
 * Auto Memory Hook - Auto-save memory files at end of session
 * Stub file for Claude Code hook system
 */

export default async function autoMemoryHook(context) {
  try {
    // This hook is managed by Claude Code auto-memory system
    // No action needed in this stub - context is preserved automatically
    return { success: true };
  } catch (error) {
    console.error('Auto-memory hook error:', error.message);
    // Non-blocking error - don't fail the session
    return { success: false, error: error.message };
  }
}
