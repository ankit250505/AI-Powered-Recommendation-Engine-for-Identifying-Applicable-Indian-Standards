import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const workspaceDir = "C:/Users/Ramchander Dabral/Documents/ChatGPT/SIH26108";
const sourcePath = "C:/Users/Ramchander Dabral/Downloads/SIH2026-IDEA-Presentation-Format.pptx";
const skillDir = "C:/Users/Ramchander Dabral/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations";
const pythonExecutable = "C:/Users/Ramchander Dabral/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe";
const buildDir = path.join(workspaceDir, ".pptx-build", "final-build");
const finalPath = path.join(workspaceDir, "output", "presentation", "SIH2026_Indian_Standards_Recommendation_Engine.pptx");
await fs.mkdir(buildDir, { recursive: true });
await fs.mkdir(path.dirname(finalPath), { recursive: true });

const { finalizePresentation } = await import(
  pathToFileURL(path.join(skillDir, "container_tools/artifact_tool_utils.mjs")).href
);

const deck = await PresentationFile.importPptx(await FileBlob.load(sourcePath));
deck.slides.getItem(6).delete();

const C = {
  navy: "#1F497D",
  blue: "#2F75B5",
  paleBlue: "#EAF2F8",
  orange: "#F28C28",
  paleOrange: "#FFF2E5",
  green: "#198754",
  paleGreen: "#EAF6EF",
  red: "#B5493A",
  paleRed: "#FBEDEA",
  ink: "#202B38",
  muted: "#5B6877",
  line: "#CBD5E1",
  soft: "#F6F8FA",
  white: "#FFFFFF",
};

const FONT = "Arial";

function setTitle(slide, title) {
  const shape = slide.shapes.items.find((item) => item.name === "Title 1");
  if (!shape) throw new Error(`Missing title on slide ${slide.slideNumber}`);
  shape.text = title;
}

function setTeam(slide) {
  const shape = slide.shapes.items.find((item) => item.name.startsWith("Oval"));
  if (!shape) return;
  shape.text = "[TEAM NAME]";
  shape.text.style = {
    typeface: FONT,
    fontSize: 11,
    bold: true,
    color: C.ink,
    alignment: "center",
    verticalAlignment: "middle",
    autoFit: "shrinkText",
    insets: { top: 3, right: 4, bottom: 3, left: 4 },
  };
}

function removePrompt(slide) {
  const shape = slide.shapes.items.find((item) => item.name === "TextBox 8");
  if (shape) shape.delete();
}

function addText(slide, text, position, options = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    name: options.name,
    position,
    fill: "none",
    line: { fill: "none", width: 0 },
  });
  shape.text = text;
  shape.text.style = {
    typeface: options.typeface ?? FONT,
    fontSize: options.fontSize ?? 16,
    bold: options.bold ?? false,
    color: options.color ?? C.ink,
    alignment: options.alignment ?? "left",
    verticalAlignment: options.verticalAlignment ?? "top",
    autoFit: options.autoFit ?? "shrinkText",
    lineSpacing: options.lineSpacing ?? 1.05,
    insets: options.insets ?? { top: 3, right: 4, bottom: 3, left: 4 },
  };
  return shape;
}

function addBox(slide, text, position, options = {}) {
  const shape = slide.shapes.add({
    geometry: options.geometry ?? "roundRect",
    name: options.name,
    position,
    fill: options.fill ?? C.white,
    line: options.line ?? { style: "solid", fill: options.lineColor ?? C.line, width: options.lineWidth ?? 1.2 },
    borderRadius: options.borderRadius ?? 7,
  });
  shape.text = text;
  shape.text.style = {
    typeface: options.typeface ?? FONT,
    fontSize: options.fontSize ?? 15,
    bold: options.bold ?? false,
    color: options.color ?? C.ink,
    alignment: options.alignment ?? "center",
    verticalAlignment: options.verticalAlignment ?? "middle",
    autoFit: options.autoFit ?? "shrinkText",
    lineSpacing: options.lineSpacing ?? 1.0,
    insets: options.insets ?? { top: 7, right: 7, bottom: 7, left: 7 },
  };
  return shape;
}

function addRule(slide, x, y, width, color = C.line, height = 2) {
  return slide.shapes.add({
    geometry: "rect",
    position: { left: x, top: y, width, height },
    fill: color,
    line: { fill: "none", width: 0 },
  });
}

function addArrow(slide, x, y, width = 18, height = 18, direction = "right") {
  return slide.shapes.add({
    geometry: direction === "down" ? "downArrow" : "rightArrow",
    position: { left: x, top: y, width, height },
    fill: C.navy,
    line: { fill: "none", width: 0 },
  });
}

function addSectionLabel(slide, text, x, y, width, color = C.navy) {
  addText(slide, text.toUpperCase(), { left: x, top: y, width, height: 25 }, {
    fontSize: 13,
    bold: true,
    color,
    verticalAlignment: "middle",
    insets: { top: 0, right: 2, bottom: 0, left: 2 },
  });
  addRule(slide, x, y + 27, width, color, 2);
}

function addBullets(slide, items, position, options = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    position,
    fill: "none",
    line: { fill: "none", width: 0 },
  });
  shape.text.set(items.map((item) => ({
    bulletCharacter: "•",
    marginLeft: 16 * 12700,
    indent: -9 * 12700,
    spaceAfter: (options.spaceAfterPt ?? 5) * 100,
    runs: [item],
  })));
  shape.text.style = {
    typeface: FONT,
    fontSize: options.fontSize ?? 15,
    color: options.color ?? C.ink,
    verticalAlignment: "top",
    autoFit: "shrinkText",
    lineSpacing: options.lineSpacing ?? 1.05,
    insets: { top: 2, right: 3, bottom: 2, left: 3 },
  };
  return shape;
}

function addMetric(slide, value, label, x, y, width, fill = C.paleBlue, color = C.navy) {
  const box = addBox(slide, "", { left: x, top: y, width, height: 70 }, {
    fill,
    lineColor: color,
    borderRadius: 6,
  });
  addText(slide, value, { left: x + 5, top: y + 7, width: width - 10, height: 30 }, {
    fontSize: 22,
    bold: true,
    color,
    alignment: "center",
    verticalAlignment: "middle",
    insets: { top: 0, right: 2, bottom: 0, left: 2 },
  });
  addText(slide, label, { left: x + 7, top: y + 39, width: width - 14, height: 23 }, {
    fontSize: 11.5,
    color: C.muted,
    alignment: "center",
    verticalAlignment: "middle",
    insets: { top: 0, right: 1, bottom: 0, left: 1 },
  });
  return box;
}

// Slide 1: official title-page structure.
{
  const slide = deck.slides.getItem(0);
  const subtitle = slide.shapes.items.find((item) => item.name === "Subtitle 3");
  subtitle.text = "TITLE PAGE";
  const details = slide.shapes.items.find((item) => item.name === "TextBox 9");
  details.position = { left: 42, top: 205, width: 650, height: 470 };
  details.text.set([
    { runs: [{ run: "Problem Statement ID - ", textStyle: { bold: true } }, "[PROBLEM STATEMENT ID]"], spaceAfter: 900 },
    { runs: [{ run: "Problem Statement Title -", textStyle: { bold: true } }], spaceAfter: 250 },
    { runs: ["AI-Powered Recommendation Engine for Identifying Applicable Indian Standards for Procurement Specifications"], spaceAfter: 900 },
    { runs: [{ run: "Theme - ", textStyle: { bold: true } }, "[THEME]"], spaceAfter: 900 },
    { runs: [{ run: "PS Category - ", textStyle: { bold: true } }, "Software"], spaceAfter: 900 },
    { runs: [{ run: "Team ID - ", textStyle: { bold: true } }, "[TEAM ID]"], spaceAfter: 900 },
    { runs: [{ run: "Team Name (Registered on portal) - ", textStyle: { bold: true } }, "[TEAM NAME]"] },
  ]);
  details.text.style = {
    typeface: FONT,
    fontSize: 17,
    color: C.ink,
    autoFit: "shrinkText",
    lineSpacing: 1.08,
    insets: { top: 4, right: 6, bottom: 4, left: 4 },
  };
}

// Slide 2: problem, solution flow, and innovation.
{
  const slide = deck.slides.getItem(1);
  setTitle(slide, "IDEA TITLE");
  setTeam(slide);
  removePrompt(slide);

  addBox(
    slide,
    "Procurement specifications often combine several technical requirements. Finding potentially applicable Indian Standards is slow, terminology-dependent, and difficult to audit.",
    { left: 55, top: 128, width: 1170, height: 62 },
    { fill: C.paleOrange, lineColor: C.orange, fontSize: 16, color: C.ink, alignment: "left", insets: { top: 10, right: 15, bottom: 8, left: 15 } },
  );

  const steps = [
    "Procurement\nspecification",
    "Text / document\nprocessing",
    "Clause\nanalysis",
    "Keyword + semantic\nretrieval",
    "Ranked\nstandards",
    "Evidence +\nexplanation",
    "Human\nverification",
    "PDF / CSV\nreport",
  ];
  const startX = 52;
  const boxW = 135;
  const gap = 12;
  steps.forEach((step, index) => {
    const x = startX + index * (boxW + gap);
    addBox(slide, step, { left: x, top: 218, width: boxW, height: 76 }, {
      fill: index < 4 ? C.paleBlue : C.paleGreen,
      lineColor: index < 4 ? C.blue : C.green,
      fontSize: 12.5,
      bold: true,
    });
    if (index < steps.length - 1) addArrow(slide, x + boxW + 1, 247, 11, 17);
  });

  addSectionLabel(slide, "Proposed solution", 58, 330, 540, C.navy);
  addBullets(slide, [
    "Accepts typed requirements and TXT, PDF, or DOCX files",
    "Splits documents into clauses before matching standards",
    "Ranks candidates using lexical and semantic relevance",
    "Returns evidence for a reviewer before export",
  ], { left: 58, top: 365, width: 550, height: 190 }, { fontSize: 15.5, spaceAfterPt: 7 });

  addSectionLabel(slide, "Innovation and uniqueness", 660, 330, 560, C.green);
  addBullets(slide, [
    "Clause-level procurement analysis across multiple requirements",
    "Keyword, local hybrid, and transformer embedding retrieval",
    "Evidence-backed results with verification status",
    "Human review, feedback, audit history, and quality monitoring",
  ], { left: 660, top: 365, width: 560, height: 190 }, { fontSize: 15.5, spaceAfterPt: 7 });

  addBox(slide, "Decision support for technical review. The system does not make a legal determination of applicability.",
    { left: 250, top: 585, width: 780, height: 43 },
    { fill: C.soft, lineColor: C.line, fontSize: 13.5, color: C.muted, bold: true });
}

// Slide 3: technical architecture and implementation stack.
{
  const slide = deck.slides.getItem(2);
  setTitle(slide, "TECHNICAL APPROACH");
  setTeam(slide);
  removePrompt(slide);

  const top = [
    ["USER", "Procurement / reviewer / admin"],
    ["WEB FRONTEND", "HTML, CSS, JavaScript"],
    ["FASTAPI BACKEND", "Authentication + API"],
    ["DOCUMENT PROCESSING", "TXT, PDF, DOCX"],
    ["CLAUSE ANALYSIS", "Split + aggregate evidence"],
  ];
  top.forEach(([heading, detail], index) => {
    const x = 52 + index * 237;
    addBox(slide, `${heading}\n${detail}`, { left: x, top: 132, width: 205, height: 72 }, {
      fill: index % 2 === 0 ? C.paleBlue : C.soft,
      lineColor: C.blue,
      fontSize: 12.5,
      bold: true,
    });
    if (index < top.length - 1) addArrow(slide, x + 209, 158, 20, 18);
  });
  addArrow(slide, 623, 211, 22, 22, "down");

  addBox(slide, "", { left: 92, top: 245, width: 1096, height: 174 }, {
    fill: C.soft,
    lineColor: C.navy,
    lineWidth: 1.5,
    borderRadius: 7,
  });
  addText(slide, "RECOMMENDATION ENGINE", { left: 110, top: 255, width: 1060, height: 31 }, {
    fontSize: 16,
    bold: true,
    color: C.navy,
    alignment: "center",
    verticalAlignment: "middle",
  });
  const engines = [
    ["KEYWORD RETRIEVAL", "Weighted title, keywords, related terms, examples"],
    ["HYBRID RETRIEVAL", "Keyword score + local similarity features"],
    ["TRANSFORMER EMBEDDINGS", "all-MiniLM-L6-v2 semantic similarity"],
  ];
  engines.forEach(([heading, detail], index) => {
    addBox(slide, `${heading}\n${detail}`, { left: 120 + index * 350, top: 302, width: 320, height: 91 }, {
      fill: index === 2 ? C.paleOrange : C.white,
      lineColor: index === 2 ? C.orange : C.blue,
      fontSize: 13,
      bold: true,
    });
  });

  addArrow(slide, 623, 425, 22, 22, "down");
  const bottom = [
    ["RANKING + EVIDENCE", C.paleBlue, C.blue],
    ["HUMAN REVIEW / VERIFICATION", C.paleGreen, C.green],
    ["SQLITE + PDF / CSV REPORTS", C.paleOrange, C.orange],
  ];
  bottom.forEach(([text, fill, line], index) => {
    const x = 130 + index * 355;
    addBox(slide, text, { left: x, top: 463, width: 310, height: 62 }, {
      fill,
      lineColor: line,
      fontSize: 14,
      bold: true,
    });
    if (index < bottom.length - 1) addArrow(slide, x + 320, 484, 22, 18);
  });

  addText(slide, "IMPLEMENTED STACK", { left: 55, top: 565, width: 165, height: 26 }, {
    fontSize: 13,
    bold: true,
    color: C.navy,
    verticalAlignment: "middle",
  });
  addBox(slide,
    "Python  |  FastAPI  |  HTML / CSS / JavaScript  |  SQLite  |  Sentence Transformers  |  Docker Compose  |  Automated tests  |  JSON logs + metrics",
    { left: 220, top: 556, width: 1005, height: 45 },
    { fill: C.white, lineColor: C.line, fontSize: 13.2, color: C.ink, alignment: "left", insets: { top: 8, right: 12, bottom: 7, left: 12 } },
  );
  addText(slide, "INPUT  >  EXTRACT  >  ANALYSE  >  RETRIEVE  >  RANK  >  EXPLAIN  >  VERIFY  >  REPORT",
    { left: 210, top: 612, width: 860, height: 29 },
    { fontSize: 14, bold: true, color: C.green, alignment: "center", verticalAlignment: "middle" });
}

// Slide 4: feasibility, risks, and response strategy.
{
  const slide = deck.slides.getItem(3);
  setTitle(slide, "FEASIBILITY AND VIABILITY");
  setTeam(slide);
  removePrompt(slide);

  addText(slide, "CONTROLLED / SYNTHETIC HELD-OUT EVALUATION RESULTS", { left: 54, top: 126, width: 350, height: 28 }, {
    fontSize: 12.5, bold: true, color: C.navy, verticalAlignment: "middle",
  });
  addMetric(slide, "91.5%", "Top-1 accuracy", 420, 119, 170, C.paleBlue, C.navy);
  addMetric(slide, "97.3%", "Top-5 accuracy", 608, 119, 170, C.paleGreen, C.green);
  addMetric(slide, "0.943", "Mean reciprocal rank", 796, 119, 180, C.paleOrange, C.orange);
  addMetric(slide, "35", "Automated tests passing", 994, 119, 230, C.soft, C.navy);

  const cols = [
    {
      x: 48, heading: "CURRENT IMPLEMENTATION", color: C.green, fill: C.paleGreen,
      items: [
        "Working FastAPI web prototype",
        "Text and multi-format document input",
        "Three retrieval strategies",
        "SQLite persistence and role workflows",
        "Automated tests and evaluation pipeline",
        "Docker, health, logging, metrics, backups",
      ],
    },
    {
      x: 449, heading: "CHALLENGES AND RISKS", color: C.red, fill: C.paleRed,
      items: [
        "Catalogue still needs authoritative verification",
        "Real specifications vary in structure and vocabulary",
        "Ambiguous domain terminology can create false positives",
        "Standards, revisions, and mandates change over time",
        "Synthetic evaluation does not prove field performance",
        "Production scale requires stronger infrastructure",
      ],
    },
    {
      x: 850, heading: "MITIGATION AND NEXT STEPS", color: C.navy, fill: C.paleBlue,
      items: [
        "Human review before procurement decisions",
        "Evidence, source status, and audit history",
        "Feedback collection and continuous evaluation",
        "Periodic BIS and government source updates",
        "Validation on genuine procurement documents",
        "HTTPS, off-host backups, and monitored deployment",
      ],
    },
  ];
  cols.forEach((col) => {
    addBox(slide, "", { left: col.x, top: 220, width: 382, height: 405 }, {
      fill: col.fill,
      lineColor: col.color,
      lineWidth: 1.4,
      borderRadius: 7,
    });
    addText(slide, col.heading, { left: col.x + 16, top: 237, width: 350, height: 38 }, {
      fontSize: 15,
      bold: true,
      color: col.color,
      alignment: "center",
      verticalAlignment: "middle",
    });
    addRule(slide, col.x + 20, 281, 342, col.color, 2);
    addBullets(slide, col.items, { left: col.x + 22, top: 300, width: 338, height: 298 }, {
      fontSize: 14.2,
      spaceAfterPt: 8,
      lineSpacing: 1.02,
    });
  });
}

// Slide 5: target users, workflow change, and benefits.
{
  const slide = deck.slides.getItem(4);
  setTitle(slide, "IMPACT AND BENEFITS");
  setTeam(slide);
  removePrompt(slide);

  addText(slide, "TARGET USERS", { left: 54, top: 128, width: 120, height: 26 }, {
    fontSize: 13, bold: true, color: C.navy, verticalAlignment: "middle",
  });
  const users = ["Procurement teams", "Government departments", "Reviewers", "Compliance teams", "Technical evaluators", "Specification authors"];
  users.forEach((user, index) => {
    addBox(slide, user, { left: 174 + index * 173, top: 121, width: 160, height: 40 }, {
      fill: index % 2 === 0 ? C.paleBlue : C.paleGreen,
      lineColor: index % 2 === 0 ? C.blue : C.green,
      fontSize: 11.5,
      bold: true,
    });
  });

  addSectionLabel(slide, "Current manual process", 62, 191, 530, C.red);
  addSectionLabel(slide, "Proposed workflow", 688, 191, 530, C.green);
  const manual = ["Specification", "Manual searching", "Technical interpretation", "Standards verification", "Documentation"];
  const proposed = ["Specification", "Clause analysis", "Ranked standards", "Evidence + human verification", "PDF / CSV report"];
  manual.forEach((item, index) => {
    const x = 63 + index * 107;
    addBox(slide, item, { left: x, top: 235, width: 96, height: 84 }, {
      fill: C.paleRed,
      lineColor: C.red,
      fontSize: item === "Documentation" ? 10.4 : 11.2,
      bold: true,
    });
    if (index < manual.length - 1) addArrow(slide, x + 97, 268, 10, 16);
  });
  proposed.forEach((item, index) => {
    const x = 688 + index * 107;
    addBox(slide, item, { left: x, top: 235, width: 96, height: 84 }, {
      fill: C.paleGreen,
      lineColor: C.green,
      fontSize: 11.2,
      bold: true,
    });
    if (index < proposed.length - 1) addArrow(slide, x + 97, 268, 10, 16);
  });

  const benefits = [
    {
      heading: "SOCIAL / GOVERNANCE", x: 62, color: C.navy, fill: C.paleBlue,
      items: ["More consistent standards discovery", "Traceable evidence and decisions", "Recommendations remain human-verifiable"],
    },
    {
      heading: "ECONOMIC / OPERATIONAL", x: 465, color: C.orange, fill: C.paleOrange,
      items: ["Faster initial standards discovery", "Less repetitive manual searching", "Structured review and report workflow"],
    },
    {
      heading: "TECHNICAL", x: 868, color: C.green, fill: C.paleGreen,
      items: ["Semantic and lexical retrieval", "Clause-level explainable evidence", "Extensible catalogue with audit history"],
    },
  ];
  benefits.forEach((benefit) => {
    addBox(slide, "", { left: benefit.x, top: 365, width: 350, height: 240 }, {
      fill: benefit.fill,
      lineColor: benefit.color,
      borderRadius: 7,
    });
    addText(slide, benefit.heading, { left: benefit.x + 15, top: 383, width: 320, height: 34 }, {
      fontSize: 14.5,
      bold: true,
      color: benefit.color,
      alignment: "center",
      verticalAlignment: "middle",
    });
    addBullets(slide, benefit.items, { left: benefit.x + 25, top: 438, width: 300, height: 140 }, {
      fontSize: 14.5,
      spaceAfterPt: 9,
    });
  });
  addText(slide, "Expected benefit: stronger decision support and traceability. Compliance and savings are not guaranteed.",
    { left: 226, top: 616, width: 828, height: 27 },
    { fontSize: 12.5, bold: true, color: C.muted, alignment: "center", verticalAlignment: "middle" });
}

// Slide 6: concise external references and internal project evidence.
{
  const slide = deck.slides.getItem(5);
  setTitle(slide, "RESEARCH AND REFERENCES");
  setTeam(slide);
  removePrompt(slide);

  addBox(slide, "", { left: 55, top: 132, width: 570, height: 420 }, {
    fill: C.paleBlue,
    lineColor: C.blue,
    borderRadius: 7,
  });
  addText(slide, "EXTERNAL REFERENCES", { left: 78, top: 151, width: 524, height: 35 }, {
    fontSize: 17, bold: true, color: C.navy, alignment: "center", verticalAlignment: "middle",
  });
  addRule(slide, 82, 194, 516, C.blue, 2);
  const external = [
    ["Bureau of Indian Standards", "bis.gov.in/know-your-standard"],
    ["Sentence Transformers and all-MiniLM-L6-v2", "sbert.net/docs"],
    ["FastAPI documentation", "fastapi.tiangolo.com"],
    ["Python documentation", "docs.python.org/3"],
    ["SQLite documentation", "sqlite.org/docs.html"],
    ["Docker documentation", "docs.docker.com"],
  ];
  external.forEach(([name, url], index) => {
    const y = 211 + index * 52;
    addText(slide, name, { left: 88, top: y, width: 320, height: 24 }, { fontSize: 14, bold: true, color: C.ink });
    addText(slide, url, { left: 405, top: y, width: 190, height: 24 }, { fontSize: 11.5, color: C.blue, alignment: "right" });
    if (index < external.length - 1) addRule(slide, 90, y + 35, 500, C.line, 1);
  });

  addBox(slide, "", { left: 655, top: 132, width: 570, height: 420 }, {
    fill: C.paleGreen,
    lineColor: C.green,
    borderRadius: 7,
  });
  addText(slide, "PROJECT RESEARCH / EVALUATION", { left: 678, top: 151, width: 524, height: 35 }, {
    fontSize: 17, bold: true, color: C.green, alignment: "center", verticalAlignment: "middle",
  });
  addRule(slide, 682, 194, 516, C.green, 2);
  addBullets(slide, [
    "250-record Indian Standards seed catalogue",
    "3,750 synthetic / controlled procurement-query examples",
    "Fixed train, validation, and held-out test splits",
    "Controlled held-out retrieval evaluation",
    "35-test automated prototype suite",
    "Verification queue, audit history, and reviewer labels",
  ], { left: 690, top: 220, width: 495, height: 275 }, { fontSize: 15.2, spaceAfterPt: 10 });
  addText(slide, "Scope disclosure", { left: 690, top: 493, width: 135, height: 28 }, {
    fontSize: 13, bold: true, color: C.green, verticalAlignment: "middle",
  });
  addText(slide, "The catalogue is not fully officially verified. Controlled metrics do not represent general real-world tender accuracy.",
    { left: 825, top: 486, width: 360, height: 48 },
    { fontSize: 12.3, color: C.muted, alignment: "left", verticalAlignment: "middle" });

  addBox(slide, "Controlled / synthetic held-out results", { left: 112, top: 579, width: 260, height: 45 }, {
    fill: C.soft, lineColor: C.line, fontSize: 12.5, bold: true, color: C.navy,
  });
  addMetric(slide, "91.5%", "Top-1", 390, 566, 150, C.paleBlue, C.navy);
  addMetric(slide, "97.3%", "Top-5", 560, 566, 150, C.paleGreen, C.green);
  addMetric(slide, "0.943", "MRR", 730, 566, 150, C.paleOrange, C.orange);
  addBox(slide, "Human review remains mandatory", { left: 900, top: 579, width: 270, height: 45 }, {
    fill: C.paleRed, lineColor: C.red, fontSize: 12.5, bold: true, color: C.red,
  });

  slide.speakerNotes.textFrame.setText([
    "External references:",
    "https://www.bis.gov.in/know-your-standard/?lang=en",
    "https://www.sbert.net/docs/sentence_transformer/pretrained_models.html",
    "https://fastapi.tiangolo.com/",
    "https://docs.python.org/3/",
    "https://www.sqlite.org/docs.html",
    "https://docs.docker.com/",
    "Project evidence: data/README.md, data/retrieval_quality.json, tests/, PROJECT_CONTEXT.md",
  ].join("\n"));
}

// Add short notes for presentation delivery and provenance.
deck.slides.getItem(1).speakerNotes.textFrame.setText(
  "Describe the system as semantic retrieval and recommendation, not a generative chatbot. Emphasize human verification and decision support.",
);
deck.slides.getItem(2).speakerNotes.textFrame.setText(
  "Hybrid mode is the measured default. Only embedding mode uses all-MiniLM-L6-v2; hybrid uses keyword scoring plus local similarity features.",
);
deck.slides.getItem(3).speakerNotes.textFrame.setText(
  "Metrics shown are controlled/synthetic held-out evaluation results from 375 test queries. They do not represent general real-world tender accuracy.",
);

const montage = await deck.export({ format: "png", montage: { columns: 3, padding: 12, gap: 12 }, scale: 1 });
await fs.writeFile(path.join(buildDir, "draft-montage.png"), new Uint8Array(await montage.arrayBuffer()));
for (let index = 0; index < deck.slides.items.length; index += 1) {
  const image = await deck.slides.getItem(index).export({ format: "png", scale: 1.5 });
  await fs.writeFile(path.join(buildDir, `draft-slide-${index + 1}.png`), new Uint8Array(await image.arrayBuffer()));
}

const candidatePath = path.join(buildDir, "candidate.pptx");
await (await PresentationFile.exportPptx(deck)).save(candidatePath);

const sourceBytes = await fs.readFile(sourcePath);
const fontPolicy = {
  basis: "reference",
      families: ["Arial", "Calibri", "Times New Roman", "TradeGothic", "Garamond"],
  referencePath: sourcePath,
  referenceSha256: crypto.createHash("sha256").update(sourceBytes).digest("hex"),
};
const requirements = {
  explicitTotalSlideCount: 6,
  requiredNativeTableOwnerSlides: [],
  requiredNativeChartOwnerSlides: [],
};
const result = await finalizePresentation({
  ...requirements,
  workspaceDir,
  candidatePath,
  finalPath,
  pythonExecutable,
  integrityValidatorPath: path.join(skillDir, "container_tools/inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(skillDir, "container_tools/inspect_presentation_layout_geometry.py"),
  layoutArgs: [
    "--expected-slide-size-emu", "12192000,6858000",
    "--expected-slide-count", "6",
    "--cover-role", "cover",
    "--validate-bullet-geometry",
    "--validate-heading-fit",
  ],
  requiredNativeTableOwnerSlides: [],
  requiredNativeChartOwnerSlides: [],
  fontPolicy,
  verifyArtifactToolImport: true,
  receiptPath: path.join(buildDir, "validation.json"),
});

console.log(JSON.stringify({ finalPath, validation: result }, null, 2));
