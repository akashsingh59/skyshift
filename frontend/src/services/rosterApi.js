const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

export async function generateRoster(payload) {
  const response = await fetch(`${apiBaseUrl}/api/roster/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

    if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || "Failed to generate roster");
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  window.open(url, "_blank", "noopener,noreferrer");
}
