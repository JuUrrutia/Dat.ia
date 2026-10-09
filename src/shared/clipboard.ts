/**
 * Clipboard write that reports honestly.
 *
 * `navigator.clipboard` only exists in a secure context. `http://localhost`
 * counts as one, so this worked in local dev, but the documented on-prem
 * deployment is a LAN address (`http://192.168.1.5:5173`), where the API is
 * `undefined` and `navigator.clipboard.writeText` throws a TypeError.
 *
 * Every call site set its "Copiado" state immediately after the call and
 * outside any promise, so on failure the UI claimed success while the
 * clipboard still held whatever was there before — the user then pasted stale
 * content into a slide.
 *
 * Returns false instead of throwing; callers gate their success state on it.
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    if (typeof navigator === 'undefined' || !navigator.clipboard?.writeText) return false;
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}