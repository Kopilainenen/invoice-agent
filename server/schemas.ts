import { z } from "zod";

const nullableText = z.string().trim().max(500).nullable();
const nullableMoney = z.number().finite().nonnegative().max(1_000_000_000_000).nullable();

const partySchema = z.object({
  name: nullableText,
  inn: z.string().regex(/^\d{10}(\d{2})?$/).nullable(),
  kpp: z.string().regex(/^\d{9}$/).nullable(),
  bank_account: z.string().regex(/^\d{20}$/).nullable(),
  bank_name: nullableText,
  bik: z.string().regex(/^\d{9}$/).nullable(),
}).strict();

const itemSchema = z.object({
  line_number: z.number().int().positive().max(10_000),
  name: z.string().trim().min(1).max(1_000),
  unit: z.string().trim().max(30).nullable(),
  quantity: z.number().finite().nonnegative().max(1_000_000_000).nullable(),
  unit_price: nullableMoney,
  line_total: nullableMoney,
}).strict();

export const invoiceSchema = z.object({
  source_file: z.string().trim().min(1).max(255),
  document_type: z.literal("invoice_for_payment"),
  supplier: partySchema,
  buyer: partySchema.nullable(),
  invoice_number: nullableText,
  invoice_date: nullableText,
  currency: z.enum(["RUB", "USD", "EUR"]).nullable(),
  subtotal_amount: nullableMoney,
  vat_amount: nullableMoney,
  vat_rate: z.number().finite().min(0).max(100).nullable(),
  total_amount: nullableMoney,
  payment_deadline: nullableText,
  contract_number: nullableText,
  items: z.array(itemSchema).max(500),
  confidence: z.record(z.string().max(100), z.number().finite().min(0).max(1)),
  warnings: z.array(z.string().max(1_000)).max(100),
  reviewed: z.boolean().optional(),
  validationIssueCount: z.number().int().nonnegative().max(10_000).optional(),
}).strict();

export const exportBodySchema = z.object({
  records: z.array(invoiceSchema).min(1).max(20),
}).strict();

export type Invoice = z.infer<typeof invoiceSchema>;
