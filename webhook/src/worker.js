// Phase 2: Instagram Messaging Webhook → Discord 通知（受信のみ・自動返信なし）
//
// GET  : Webhook 検証（hub.challenge を返す）
// POST : messages イベントを受信し、送信者ID＋本文の概要を Discord へ転送
//
// 受信購読のみのため自動返信はせず、24時間ルール等の送信制約は不要。
// 必要権限（最小）: instagram_business_manage_messages（受信）。
// Secrets: IG_VERIFY_TOKEN, DISCORD_WEBHOOK_URL, IG_APP_SECRET(任意)

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // 1) Webhook 検証
    if (request.method === "GET") {
      const mode = url.searchParams.get("hub.mode");
      const token = url.searchParams.get("hub.verify_token");
      const challenge = url.searchParams.get("hub.challenge");
      if (mode === "subscribe" && token === env.IG_VERIFY_TOKEN) {
        return new Response(challenge, { status: 200 });
      }
      return new Response("forbidden", { status: 403 });
    }

    // 2) イベント受信
    if (request.method === "POST") {
      const raw = await request.text();

      // 任意: 署名検証（IG_APP_SECRET 設定時のみ）
      if (env.IG_APP_SECRET) {
        const ok = await verifySignature(raw, request.headers.get("x-hub-signature-256"), env.IG_APP_SECRET);
        if (!ok) return new Response("bad signature", { status: 401 });
      }

      let body;
      try { body = JSON.parse(raw); } catch { return new Response("ok", { status: 200 }); }

      const lines = [];
      for (const entry of body.entry || []) {
        for (const ev of entry.messaging || []) {
          if (ev.message && !ev.message.is_echo) {
            const from = ev.sender?.id ?? "unknown";
            const text = ev.message.text ?? "（テキストなし: 画像/スタンプ等）";
            lines.push(`📩 **新規DM**\n送信者ID: \`${from}\`\n本文: ${text}`);
          }
        }
      }

      if (lines.length && env.DISCORD_WEBHOOK_URL) {
        await fetch(env.DISCORD_WEBHOOK_URL, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ content: lines.join("\n\n").slice(0, 1900) }),
        });
      }

      // Meta には常に即 200（再送ループ防止）
      return new Response("ok", { status: 200 });
    }

    return new Response("method not allowed", { status: 405 });
  },
};

async function verifySignature(raw, header, secret) {
  if (!header) return false;
  const expected = header.replace("sha256=", "");
  const key = await crypto.subtle.importKey(
    "raw", new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" }, false, ["sign"],
  );
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(raw));
  const hex = [...new Uint8Array(sig)].map((b) => b.toString(16).padStart(2, "0")).join("");
  return timingSafeEqual(hex, expected);
}

function timingSafeEqual(a, b) {
  if (a.length !== b.length) return false;
  let out = 0;
  for (let i = 0; i < a.length; i++) out |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return out === 0;
}
