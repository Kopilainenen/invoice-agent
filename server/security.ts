import { timingSafeEqual } from "node:crypto";

export const MAX_FILE_SIZE = 12 * 1024 * 1024;
export const MAX_FILES = 20;

const signatures = [
  { suffix: ".pdf", bytes: Buffer.from("%PDF-") },
  { suffix: ".png", bytes: Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]) },
  { suffix: ".jpg", bytes: Buffer.from([0xff, 0xd8, 0xff]) },
] as const;

export function detectFileSuffix(buffer: Buffer): ".pdf" | ".png" | ".jpg" | null {
  for (const signature of signatures) {
    if (buffer.length < signature.bytes.length) continue;
    const head = buffer.subarray(0, signature.bytes.length);
    if (timingSafeEqual(head, signature.bytes)) return signature.suffix;
  }
  return null;
}

export function safeDisplayName(value: string): string {
  const base = value.replaceAll("\\", "/").split("/").pop() ?? "document";
  return base.replace(/[\u0000-\u001f\u007f]/g, "_").slice(0, 255) || "document";
}

export function isAllowedOrigin(origin: string | undefined, port: number): boolean {
  if (!origin) return false;
  return origin === `http://127.0.0.1:${port}` || origin === `http://localhost:${port}`;
}
