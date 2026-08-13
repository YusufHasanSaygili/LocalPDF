import { expect, test } from "@playwright/test";

function onePagePdf(label: string): Buffer {
  const stream = `BT /F1 20 Tf 72 720 Td (${label.replace(/[()\\]/g, "")}) Tj ET`;
  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
    `<< /Length ${Buffer.byteLength(stream)} >>\nstream\n${stream}\nendstream`,
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
  ];
  let body = "%PDF-1.4\n";
  const offsets = [0];
  objects.forEach((object, index) => {
    offsets.push(Buffer.byteLength(body));
    body += `${index + 1} 0 obj\n${object}\nendobj\n`;
  });
  const xref = Buffer.byteLength(body);
  body += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  body += offsets.slice(1).map((offset) => `${String(offset).padStart(10, "0")} 00000 n \n`).join("");
  body += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  return Buffer.from(body);
}

test("upload, merge, download and audited export", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Düşük riskli kişisel kullanım içindir.")).toBeVisible();

  const input = page.locator('input[type="file"]');
  await input.setInputFiles([
    { name: "birinci.pdf", mimeType: "application/pdf", buffer: onePagePdf("FIRST") },
    { name: "ikinci.pdf", mimeType: "application/pdf", buffer: onePagePdf("SECOND") },
  ]);
  await expect(page.getByText("birinci.pdf")).toBeVisible();
  await expect(page.getByText("ikinci.pdf")).toBeVisible();

  await page.locator(".merge-check input").nth(0).check();
  await page.locator(".merge-check input").nth(1).check();
  await page.getByRole("button", { name: "Birleştir işlemini başlat" }).click();
  await expect(page.getByText("Yeni sürüm hazır")).toBeVisible({ timeout: 60_000 });
  await expect(page.locator(".version-pill").first()).toContainText("v1");

  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("link", { name: "İndir" }).click();
  const download = await downloadPromise;
  expect(await download.failure()).toBeNull();

  await page.getByRole("button", { name: "Audit" }).click();
  await expect(page.getByText("operation.succeeded")).toBeVisible();
});

