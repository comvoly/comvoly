const READ_SIZE = 1024 * 1024;
const IMPORT_BATCH_SIZE = 200;
const MEDIA_KEYS = ["photo", "file", "thumbnail", "sticker_file", "contact_vcard"] as const;

export type TelegramExportHeader = {
  parser_version: "telegram-desktop-json-v1";
  external_community_id: string;
  community_name: string;
  export_type: string;
};

export type TelegramStreamSummary = TelegramExportHeader & {
  message_count: number;
  service_event_count: number;
  participant_count: number;
  media_count: number;
  history_start: string | null;
  history_end: string | null;
  warnings: string[];
};

export type TelegramStreamCallbacks = {
  onHeader: (header: TelegramExportHeader) => Promise<void> | void;
  onBatch: (messages: Record<string, unknown>[], chunkIndex: number,
            bytesProcessed: number) => Promise<void> | void;
  onProgress?: (bytesProcessed: number, bytesTotal: number,
                messagesDiscovered: number) => void;
};

async function sha256(value: Uint8Array): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", value.slice().buffer as ArrayBuffer);
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

export async function telegramFileFingerprint(file: File): Promise<string> {
  const edge = 64 * 1024;
  const first = new Uint8Array(await file.slice(0, Math.min(edge, file.size)).arrayBuffer());
  const lastStart = Math.max(0, file.size - edge);
  const last = new Uint8Array(await file.slice(lastStart).arrayBuffer());
  const metadata = new TextEncoder().encode(`${file.name}\n${file.size}\n${file.lastModified}\n`);
  const combined = new Uint8Array(metadata.length + first.length + last.length);
  combined.set(metadata); combined.set(first, metadata.length); combined.set(last, metadata.length + first.length);
  return `telegram-stream-${await sha256(combined)}`;
}

async function headerFromPrefix(prefix: string): Promise<TelegramExportHeader> {
  let document: Record<string, unknown>;
  try {
    document = JSON.parse(`${prefix.replace(/^\uFEFF/, "")}"messages":[]}`) as Record<string, unknown>;
  } catch {
    throw new Error("This does not look like Telegram Desktop's result.json for one chat.");
  }
  const name = String(document.name || "").trim() || "Telegram community";
  const suppliedId = String(document.id || "").trim();
  const externalId = suppliedId || `export-fingerprint:${(await sha256(new TextEncoder().encode(name))).slice(0, 24)}`;
  return {
    parser_version: "telegram-desktop-json-v1",
    external_community_id: externalId,
    community_name: name,
    export_type: String(document.type || "unknown"),
  };
}

function messageDate(item: Record<string, unknown>): string | null {
  const supplied = String(item.date || "").trim();
  if (supplied) {
    const parsed = new Date(supplied);
    if (!Number.isNaN(parsed.valueOf())) return parsed.toISOString();
  }
  const unix = Number(String(item.date_unixtime || ""));
  if (Number.isFinite(unix) && unix > 0) return new Date(unix * 1000).toISOString();
  return null;
}

export async function streamTelegramExport(file: File,
                                           callbacks: TelegramStreamCallbacks): Promise<TelegramStreamSummary> {
  const decoder = new TextDecoder("utf-8", { fatal: true });
  let buffer = "";
  let bytesRead = 0;
  let header: TelegramExportHeader | null = null;
  let cursor = 0;
  let objectStart = -1;
  let depth = 0;
  let inString = false;
  let escaped = false;
  let ended = false;
  let chunkIndex = 0;
  let batch: Record<string, unknown>[] = [];
  let ordinary = 0;
  let service = 0;
  let media = 0;
  let invalidDates = 0;
  let historyStart: string | null = null;
  let historyEnd: string | null = null;
  const participants = new Set<string>();

  async function emitBatch() {
    if (!batch.length) return;
    const current = batch; batch = [];
    await callbacks.onBatch(current, chunkIndex, bytesRead);
    chunkIndex += 1;
  }

  function inventory(item: Record<string, unknown>) {
    if (String(item.type || "message") !== "message") { service += 1; return; }
    ordinary += 1;
    const participant = String(item.from_id || item.from || "").trim();
    if (participant) participants.add(participant);
    if (MEDIA_KEYS.some((key) => Boolean(item[key]))) media += 1;
    const date = messageDate(item);
    if (!date) invalidDates += 1;
    else {
      historyStart = !historyStart || date < historyStart ? date : historyStart;
      historyEnd = !historyEnd || date > historyEnd ? date : historyEnd;
    }
  }

  async function consumeAvailable() {
    while (cursor < buffer.length && !ended) {
      const character = buffer[cursor];
      if (objectStart < 0) {
        if (/\s|,/.test(character)) { cursor += 1; continue; }
        if (character === "]") { ended = true; cursor += 1; break; }
        if (character !== "{") throw new Error("Telegram's messages array contains unsupported JSON.");
        objectStart = cursor; depth = 0; inString = false; escaped = false;
      }
      if (inString) {
        if (escaped) escaped = false;
        else if (character === "\\") escaped = true;
        else if (character === "\"") inString = false;
      } else if (character === "\"") inString = true;
      else if (character === "{" || character === "[") depth += 1;
      else if (character === "}" || character === "]") {
        depth -= 1;
        if (depth === 0) {
          let item: Record<string, unknown>;
          try { item = JSON.parse(buffer.slice(objectStart, cursor + 1)) as Record<string, unknown>; }
          catch { throw new Error("A Telegram message in this export contains invalid JSON."); }
          inventory(item); batch.push(item); objectStart = -1;
          if (batch.length >= IMPORT_BATCH_SIZE) await emitBatch();
          if (cursor > READ_SIZE && objectStart < 0) { buffer = buffer.slice(cursor + 1); cursor = -1; }
        }
      }
      cursor += 1;
    }
  }

  for (let offset = 0; offset < file.size; offset += READ_SIZE) {
    const part = new Uint8Array(await file.slice(offset, Math.min(offset + READ_SIZE, file.size)).arrayBuffer());
    bytesRead += part.byteLength;
    try { buffer += decoder.decode(part, { stream: bytesRead < file.size }); }
    catch { throw new Error("The Telegram export is not valid UTF-8 JSON."); }
    if (!header) {
      const match = /"messages"\s*:\s*\[/.exec(buffer);
      if (!match) {
        if (buffer.length > 8 * READ_SIZE) throw new Error("Could not find Telegram's messages list near the start of the file.");
        callbacks.onProgress?.(bytesRead, file.size, ordinary + service);
        continue;
      }
      header = await headerFromPrefix(buffer.slice(0, match.index));
      await callbacks.onHeader(header);
      buffer = buffer.slice(match.index + match[0].length); cursor = 0;
    }
    await consumeAvailable();
    callbacks.onProgress?.(bytesRead, file.size, ordinary + service);
  }
  if (!header) throw new Error("Could not find a Telegram messages list in this file.");
  await consumeAvailable();
  await emitBatch();
  if (!ended) throw new Error("The Telegram export ended before its messages list was complete.");
  const warnings: string[] = [];
  if (!ordinary) warnings.push("No ordinary messages were found in this export.");
  if (invalidDates) warnings.push(`${invalidDates.toLocaleString()} messages had invalid dates and were skipped.`);
  if (!new Set(["private_group", "supergroup", "public_supergroup", "channel"]).has(header.export_type.toLowerCase()))
    warnings.push("Confirm that this export is the intended owner-authorised community chat.");
  return { ...header, message_count: ordinary, service_event_count: service,
    participant_count: participants.size, media_count: media,
    history_start: historyStart, history_end: historyEnd, warnings };
}
