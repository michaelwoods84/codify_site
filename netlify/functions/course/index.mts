// Unlocks the paid modules of the parents' course (/course/).
//
// POST /api/course  { "key": "<Gumroad licence key or admin key>", "first": true }
//
// The paid module text is stored AES-256-GCM encrypted in content.enc.mjs
// (written by parent_intro_to_ai/deploy-to-site.sh), because this repo is
// public. A valid key gets the decrypted modules back; nothing else does.
//
// Environment variables (Netlify → Project configuration → Environment variables):
//   COURSE_CONTENT_KEY  base64 32-byte key the content was encrypted with (required)
//   ADMIN_ACCESS_KEY    owner's preview key; unlocks without a purchase (optional)
//   GUMROAD_PRODUCT_ID  overrides the product ID below (optional)
import { createDecipheriv, createHash, timingSafeEqual } from "node:crypto";
import { PAYLOAD } from "./content.enc.mjs";

const DEFAULT_PRODUCT_ID = "A-yK1Z3MxMSHVlSRZUE5SQ=="; // "What Is My Child Actually Learning?"

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
  });

// Compare via hashes so differing lengths don't leak through timing.
const sameSecret = (a: string, b: string) =>
  timingSafeEqual(createHash("sha256").update(a).digest(), createHash("sha256").update(b).digest());

function decryptContent(keyB64: string) {
  const key = Buffer.from(keyB64, "base64");
  const raw = Buffer.from(PAYLOAD, "base64");
  const decipher = createDecipheriv("aes-256-gcm", key, raw.subarray(0, 12));
  decipher.setAuthTag(raw.subarray(12, 28));
  const plain = Buffer.concat([decipher.update(raw.subarray(28)), decipher.final()]);
  return JSON.parse(plain.toString("utf8"));
}

// "ok" | "invalid" | "refunded" | "unavailable"
async function checkGumroad(licenseKey: string, increment: boolean) {
  const body = new URLSearchParams({
    product_id: Netlify.env.get("GUMROAD_PRODUCT_ID") || DEFAULT_PRODUCT_ID,
    license_key: licenseKey,
    increment_uses_count: String(increment),
  });
  let res: Response;
  try {
    res = await fetch("https://api.gumroad.com/v2/licenses/verify", { method: "POST", body });
  } catch {
    return "unavailable";
  }
  const data = await res.json().catch(() => null);
  if (!data) return "unavailable";
  if (!data.success) return res.status >= 500 ? "unavailable" : "invalid";
  const p = data.purchase || {};
  if (p.refunded || p.chargebacked || p.disputed) return "refunded";
  return "ok";
}

export default async (req: Request) => {
  if (req.method !== "POST") return json(405, { ok: false, reason: "method" });

  const contentKey = Netlify.env.get("COURSE_CONTENT_KEY");
  if (!contentKey) return json(500, { ok: false, reason: "unavailable" });

  const input = await req.json().catch(() => ({}));
  const key = String(input?.key ?? "").trim();
  if (!key || key.length > 200) return json(400, { ok: false, reason: "invalid" });

  const adminKey = Netlify.env.get("ADMIN_ACCESS_KEY");
  const isAdmin = !!adminKey && sameSecret(key, adminKey);
  if (!isAdmin) {
    const result = await checkGumroad(key, input?.first === true);
    if (result !== "ok") return json(result === "unavailable" ? 502 : 403, { ok: false, reason: result });
  }

  try {
    return json(200, { ok: true, admin: isAdmin, modules: decryptContent(contentKey) });
  } catch {
    return json(500, { ok: false, reason: "unavailable" });
  }
};

export const config = { path: "/api/course" };
