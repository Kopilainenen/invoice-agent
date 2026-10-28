import { randomUUID } from "node:crypto";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

import helmet from "@fastify/helmet";
import multipart from "@fastify/multipart";
import rateLimit from "@fastify/rate-limit";
import fastifyStatic from "@fastify/static";
import Fastify from "fastify";
import { ZodError } from "zod";

import { runPython } from "./python.js";
import { exportBodySchema, invoiceSchema, type Invoice } from "./schemas.js";
import {
  detectFileSuffix,
  isAllowedOrigin,
  MAX_FILES,
  MAX_FILE_SIZE,
  safeDisplayName,
} from "./security.js";

const serverDirectory = path.dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = path.resolve(serverDirectory, "..");
const WEB_ROOT = path.join(PROJECT_ROOT, "web");
const HOST = "127.0.0.1";
const configuredPort = Number(process.env.INVOICE_AGENT_PORT ?? "8765");
if (!Number.isInteger(configuredPort) || configuredPort < 1024 || configuredPort > 65535) {
  throw new Error("INVOICE_AGENT_PORT должен быть целым числом от 1024 до 65535");
}
const PORT = configuredPort;

const app = Fastify({
  logger: { level: "info", redact: ["req.headers.cookie", "req.headers.authorization"] },
  bodyLimit: 8 * 1024 * 1024,
  requestTimeout: 190_000,
  connectionTimeout: 10_000,
  keepAliveTimeout: 5_000,
  routerOptions: { maxParamLength: 100 },
  trustProxy: false,
});

await app.register(helmet, {
  global: true,
  contentSecurityPolicy: {
    useDefaults: false,
    directives: {
      defaultSrc: ["'self'"],
      scriptSrc: ["'self'"],
      styleSrc: ["'self'"],
      imgSrc: ["'self'", "blob:", "data:"],
      frameSrc: ["'self'", "blob:"],
      connectSrc: ["'self'"],
      objectSrc: ["'none'"],
      baseUri: ["'none'"],
      formAction: ["'self'"],
      frameAncestors: ["'none'"],
    },
  },
  crossOriginEmbedderPolicy: false,
  hsts: false,
});

await app.register(rateLimit, {
  max: 60,
  timeWindow: "1 minute",
  ban: 3,
  keyGenerator: (request) => request.ip,
});

await app.register(multipart, {
  throwFileSizeLimit: true,
  limits: {
    files: MAX_FILES,
    fileSize: MAX_FILE_SIZE,
    fields: 0,
    parts: MAX_FILES,
    headerPairs: 50,
  },
});

await app.register(fastifyStatic, {
  root: WEB_ROOT,
  wildcard: false,
  index: ["index.html"],
  dotfiles: "deny",
  cacheControl: false,
  etag: false,
});

app.addHook("onRequest", async (request, reply) => {
  if (request.method === "POST") {
    const marker = request.headers["x-invoice-agent"];
    if (marker !== "1" || !isAllowedOrigin(request.headers.origin, PORT)) {
      return reply.code(403).send({ error: "Запрос отклонён проверкой источника" });
    }
  }
});

app.addHook("onSend", async (_request, reply, payload) => {
  reply.header("Cache-Control", "no-store");
  reply.header("X-Content-Type-Options", "nosniff");
  return payload;
});

app.get("/health", async () => ({ status: "ok", runtime: "typescript" }));

app.post("/api/extract", {
  config: { rateLimit: { max: 10, timeWindow: "1 minute" } },
}, async (request, reply) => {
  const workingDirectory = await mkdtemp(path.join(tmpdir(), "invoice-agent-"));
  const records: Invoice[] = [];
  const errors: Array<{ file: string; error: string }> = [];
  let count = 0;
  try {
    for await (const part of request.files()) {
      count += 1;
      if (count > MAX_FILES) throw new Error("Слишком много файлов");
      const displayName = safeDisplayName(part.filename);
      try {
        const buffer = await part.toBuffer();
        const suffix = detectFileSuffix(buffer);
        if (!suffix) {
          errors.push({ file: displayName, error: "Содержимое не является PDF, PNG или JPEG" });
          continue;
        }
        const input = path.join(workingDirectory, `${randomUUID()}${suffix}`);
        const output = path.join(workingDirectory, `${randomUUID()}.json`);
        await writeFile(input, buffer, { flag: "wx", mode: 0o600 });
        await runPython(PROJECT_ROOT, ["extract", input, output]);
        const parsed: unknown = JSON.parse(await readFile(output, "utf8"));
        const record = invoiceSchema.parse({ ...parsed as object, source_file: displayName });
        records.push(record);
      } catch (error) {
        const message = error instanceof Error ? error.message : "Ошибка обработки";
        errors.push({ file: displayName, error: message.slice(0, 500) });
      }
    }
  } finally {
    await rm(workingDirectory, { recursive: true, force: true });
  }
  if (count === 0) return reply.code(400).send({ error: "Файлы не переданы" });
  if (records.length === 0) return reply.code(400).send({ error: errors[0]?.error ?? "Документы не обработаны" });
  return { records, errors };
});

app.post<{ Querystring: { format?: string } }>("/api/export", async (request, reply) => {
  const format = request.query.format;
  if (format !== "csv" && format !== "xlsx") {
    return reply.code(400).send({ error: "Поддерживается экспорт CSV или XLSX" });
  }
  const { records } = exportBodySchema.parse(request.body);
  const workingDirectory = await mkdtemp(path.join(tmpdir(), "invoice-agent-export-"));
  try {
    const input = path.join(workingDirectory, "records.json");
    const output = path.join(workingDirectory, `invoice-register.${format}`);
    await writeFile(input, JSON.stringify(records), { flag: "wx", mode: 0o600 });
    await runPython(PROJECT_ROOT, ["export", format, input, output], 30_000);
    const body = await readFile(output);
    reply.type(format === "csv" ? "text/csv; charset=utf-8" : "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
    reply.header("Content-Disposition", `attachment; filename="invoice-register.${format}"`);
    return reply.send(body);
  } finally {
    await rm(workingDirectory, { recursive: true, force: true });
  }
});

app.setErrorHandler((error, _request, reply) => {
  if (error instanceof ZodError) {
    return reply.code(400).send({ error: "Некорректные данные запроса" });
  }
  const statusCode = typeof error === "object" && error !== null && "statusCode" in error
    && typeof error.statusCode === "number" ? error.statusCode : null;
  if (statusCode !== null && statusCode >= 400 && statusCode < 500) {
    return reply.code(statusCode).send({ error: "Запрос отклонён" });
  }
  app.log.error(error);
  return reply.code(500).send({ error: "Внутренняя ошибка сервера" });
});

await app.listen({ host: HOST, port: PORT });
app.log.info(`Invoice Agent: http://${HOST}:${PORT}`);
