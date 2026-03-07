export async function generateRoster(payload) {
  const response = await fetch("/api/roster/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

    if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || "Failed to generate roster");
  }

  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `roster_${payload.shift}.pdf`;
  link.click();
  window.URL.revokeObjectURL(url);
}