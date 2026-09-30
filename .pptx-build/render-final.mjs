import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const sourcePath = "C:/Users/Ramchander Dabral/Documents/ChatGPT/SIH26108/output/presentation/SIH2026_Indian_Standards_Recommendation_Engine.pptx";
const outDir = "C:/Users/Ramchander Dabral/Documents/ChatGPT/SIH26108/.pptx-build/final-render";
await fs.mkdir(outDir, { recursive: true });

const presentation = await PresentationFile.importPptx(await FileBlob.load(sourcePath));
const snapshot = await presentation.inspect({
  kind: "deck,slide,textbox,shape,image,notes,layout",
  include: "id,slide,name,title,text,textPreview,textChars,textLines,bbox,bboxUnit,isPlaceholder,alt",
  maxChars: 50000,
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
}

console.log(JSON.stringify({ slides: presentation.slides.items.length }));
