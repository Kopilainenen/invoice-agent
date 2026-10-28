import { execFile } from "node:child_process";
import { access } from "node:fs/promises";
import { homedir } from "node:os";
import path from "node:path";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

async function pythonExecutable(): Promise<string> {
  const configured = process.env.INVOICE_AGENT_PYTHON;
  if (configured) return configured;
  const bundled = path.join(
    homedir(), ".cache", "codex-runtimes", "codex-primary-runtime",
    "dependencies", "python", "python.exe",
  );
  try {
    await access(bundled);
    return bundled;
  } catch {
    return process.platform === "win32" ? "python.exe" : "python3";
  }
}

export async function runPython(
  projectRoot: string,
  args: readonly string[],
  timeout = 180_000,
): Promise<void> {
  const executable = await pythonExecutable();
  const bridge = path.join(projectRoot, "scripts", "python_bridge.py");
  await execFileAsync(executable, [bridge, ...args], {
    cwd: projectRoot,
    windowsHide: true,
    shell: false,
    timeout,
    maxBuffer: 1024 * 1024,
    env: {
      PATH: process.env.PATH,
      SYSTEMROOT: process.env.SYSTEMROOT,
      TEMP: process.env.TEMP,
      TMP: process.env.TMP,
      USERPROFILE: process.env.USERPROFILE,
      PYTHONIOENCODING: "utf-8",
      PYTHONDONTWRITEBYTECODE: "1",
    },
  });
}
