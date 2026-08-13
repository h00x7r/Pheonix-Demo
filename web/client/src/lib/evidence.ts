/** Browser-only evidence primitives: files are hashed locally and never uploaded. */
export const MAX_EVIDENCE_FILE_BYTES = 25 * 1024 * 1024;

export type FileEvidence = {
  id: string;
  name: string;
  size: number;
  type: string;
  sha256: string;
  addedAt: string;
};

export async function sha256Hex(data: ArrayBuffer): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

export async function fingerprintFile(file: File): Promise<FileEvidence> {
  if (file.size > MAX_EVIDENCE_FILE_BYTES) {
    throw new Error("الحد المحلي للملف هو 25 MB حتى لا يستهلك التحليل ذاكرة المتصفح.");
  }
  const sha256 = await sha256Hex(await file.arrayBuffer());
  return {
    id: crypto.randomUUID(),
    name: file.name,
    size: file.size,
    type: file.type || "unknown",
    sha256,
    addedAt: new Date().toISOString(),
  };
}

export function downloadJson(filename: string, payload: unknown) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
