const BASE_URL = import.meta.env.VITE_API_BASE_URL || "";
console.log("Dodge AI API Base URL:", BASE_URL || "[WARNING: BASE_URL is UNDEFINED. Using relative paths.]");

export async function fetchGraph({ billing_document, include_journal_entry, include_payments } = {}) {
  const params = new URLSearchParams();
  if (billing_document) params.set("billing_document", billing_document);
  params.set("include_journal_entry", include_journal_entry ? "true" : "false");
  params.set("include_payments", include_payments ? "true" : "false");

  const url = `${BASE_URL}/graph?${params.toString()}`;
  const res = await fetch(url, { method: "GET" });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Graph request failed: ${res.status} ${text}`);
  }
  return res.json();
}

export async function postChat(question) {
  const res = await fetch(`${BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Chat request failed: ${res.status} ${text}`);
  }
  return res.json();
}

