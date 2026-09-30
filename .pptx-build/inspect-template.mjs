import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const sourcePath = "C:/Users/Ramchander Dabral/Downloads/SIH2026-IDEA-Presentation-Format.pptx";
const outDir = "C:/Users/Ramchander Dabral/Documents/ChatGPT/SIH26108/.pptx-build/template-inspect";
await fs.mkdir(outDir, { recursive: true });

const presentation = await PresentationFile.importPptx(await FileBlob.load(sourcePath));
const snapshot = await presentation.inspect({
  kind: "deck,slide,textbox,shape,image,table,chart,notes,layout",
  include: "id,slide,name,title,text,textPreview,textChars,textLines,bbox,bboxUnit,isPlaceholder,placeholders,alt",
  maxChars: 30000,
});
await fs.writeFile(path.join(outDir, "inspect.ndjson"), snapshot.ndjson);

const montage = await presentation.export({ format: "png", montage: true, scale: 1 });
await fs.writeFile(path.join(outDir, "montage.png"), new Uint8Array(await montage.arrayBuffer()));

for (let index = 0; index < presentation.slides.items.length; index += 1) {
  const slide = presentation.slides.getItem(index);
  const preview = await slide.export({ format: "png", scale: 1.5 });
  await fs.writeFile(
    path.join(outDir, `slide-${index + 1}.png`),
    new Uint8Array(await preview.arrayBuffer()),
  );
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(path.join(outDir, `slide-${index + 1}.layout.json`), await layout.text());
}

console.log(JSON.stringify({
  slides: presentation.slides.items.length,
  masters: presentation.masters.items.length,
  layouts: presentation.layouts.items.length,
}));
