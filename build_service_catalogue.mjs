import fs from "node:fs/promises";
import { Workbook, SpreadsheetFile } from "@oai/artifact-tool";

const outDir = "outputs/finagent-architecture-freeze";
const outFile = `${outDir}/FinAgent service catalogue.xlsx`;
const navy = "#17365D";
const blue = "#D9EAF7";
const pale = "#F5F9FC";
const grid = "#D9E2F3";

function title(sheet, text, width) {
  sheet.getRange(`A2:${width}2`).merge();
  sheet.getRange("A2").values = [[text]];
  sheet.getRange("A2").format = { font: { name: "Arial", size: 16, bold: true, color: "#000000" }, verticalAlignment: "center" };
  sheet.getRange("A2").format.rowHeight = 28;
}

function header(range) {
  range.format = {
    fill: navy,
    font: { name: "Arial", size: 10, bold: true, color: "#FFFFFF" },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "all", style: "thin", color: "#FFFFFF" },
  };
}

function body(range) {
  range.format = {
    font: { name: "Arial", size: 10, color: "#1F1F1F" },
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "all", style: "thin", color: grid },
  };
}

const services = [
  ["API gateway and BFF", "Presentation", "UI-facing API, authentication propagation, rate limits", "FastAPI, Pydantic, OAuth2/OIDC", "OpenAPI v1", "API contracts", "PostgreSQL read models", "Weeks 1-2", "Modular monolith", "No decision logic"],
  ["Market data ingestion", "Data", "Fetch, validate, deduplicate, timestamp provider price data", "Python, Prefect, provider SDK", "market.raw.v1", "Raw source manifests", "Object storage", "Weeks 3-4", "Worker", "No vendor secrets in events"],
  ["Research ingestion", "Data", "Collect licensed filings, news, macro, and metadata", "Python, Prefect", "research.document.v1", "Research documents", "Object storage", "Weeks 7-8", "Worker", "Respect license and source rules"],
  ["Normalization and quality", "Data", "Canonical schemas, freshness and anomaly checks", "Python, Pydantic, Great Expectations", "market.normalized.v1", "Normalized facts and quality results", "TimescaleDB / ClickHouse", "Weeks 3-6", "Module then worker", "Fail closed on critical data quality"],
  ["Feature pipeline", "Intelligence", "Point-in-time technical, fundamental, macro and sentiment features", "Python, Polars, DuckDB, Parquet", "feature.materialized.v1", "Feature definitions and materializations", "Object storage", "Weeks 7-10", "Worker", "as_of_time required"],
  ["Research corpus", "Intelligence", "Chunk, embed, retrieve cited research", "PostgreSQL, pgvector", "Internal API", "Corpus index and citations", "PostgreSQL + pgvector", "Weeks 7-10", "Module", "No untrusted instructions as tool commands"],
  ["Agent orchestrator", "Intelligence", "Coordinate research analysts, critic, structured output", "LangGraph, LLM SDK, Pydantic", "Internal API", "Agent traces and prompt refs", "PostgreSQL + object storage", "Weeks 26-30", "Worker", "Read-only allow-listed tools"],
  ["Quant prediction", "Intelligence", "Train, score, and ensemble numeric models", "scikit-learn, LightGBM, MLflow", "Internal API", "Model outputs and versions", "MLflow + object storage", "Weeks 11-15", "Module then worker", "LLM does not set numeric forecast"],
  ["Strategy engine", "Decision", "Create versioned candidate actions from signals", "Python domain library", "signal.candidate.v1", "Strategy output and parameters", "PostgreSQL", "Weeks 11-15", "Module", "Candidate only, not an order"],
  ["Risk policy engine", "Decision", "Apply deterministic exposure, freshness, and metadata rules", "Python rules, Pydantic", "decision.risk-reviewed.v1", "Policy decision", "PostgreSQL", "Weeks 16-20", "Module", "Fail closed; agent cannot bypass"],
  ["Prediction ledger", "Decision", "Append-only decision provenance and outcomes", "PostgreSQL, Alembic", "ledger.recorded.v1", "Ledger entries", "PostgreSQL", "Weeks 16-20", "Module", "Immutable correction links"],
  ["Backtest engine", "Simulation", "Historical event/time-aware simulation", "Python, Polars, NumPy", "simulation.fill.v1", "Backtest runs", "PostgreSQL + object storage", "Weeks 16-20", "Worker", "Look-ahead bias tests"],
  ["Paper trading simulator", "Simulation", "Simulated fills, positions, costs and portfolios", "Python, PostgreSQL", "simulation.fill.v1", "Orders, fills, positions", "PostgreSQL", "Weeks 21-25", "Worker", "No broker-routing capability"],
  ["Copy shadow simulation", "Simulation", "Follow another simulated account under independent limits", "Python, PostgreSQL", "Internal API", "Shadow account relation", "PostgreSQL", "Weeks 21-25", "Module", "No real copy trading"],
  ["Evaluation and learning", "Learning", "Score outcomes, drift, attribution, candidate promotion", "Python, Evidently, MLflow", "evaluation.completed.v1", "Evaluations and gates", "PostgreSQL + MLflow", "Weeks 26-30", "Worker", "Human approval for promotion"],
  ["Registry", "Learning", "Version and promote models, strategies, prompts and policies", "MLflow, Git, object storage", "model.promotion.v1", "Registry pointers", "MLflow + Git", "Weeks 11-15", "Module", "Signed/pinned artifacts"],
  ["Observability", "Operations", "Metrics, logs, traces, audit dashboards", "OpenTelemetry, Prometheus, Grafana, Loki", "Telemetry", "Telemetry data", "Observability stack", "Weeks 31-36", "Platform", "Redact sensitive data"],
  ["Notification service", "Operations", "Deliver research and simulation alerts", "FastAPI worker, email/webhooks", "Internal API", "Delivery records", "PostgreSQL", "Weeks 31-36", "Worker", "No actionable trade instruction"],
];

const phases = [
  ["0", "Weeks 1-2", "Design and foundations", "Local dev, contracts, fixture dataset, baseline vertical slice", "Reproducible local run and architecture review"],
  ["1", "Weeks 3-6", "Data foundation", "Ingestion, normalized data, quality, storage", "Daily data is versioned, validated, replayable"],
  ["2", "Weeks 7-10", "Research and features", "Features, corpus, retrieval, cited brief", "Point-in-time features and cited briefs pass tests"],
  ["3", "Weeks 11-15", "Prediction and strategies", "Baselines, ensembles, registry, strategies", "Walk-forward benchmark and model cards"],
  ["4", "Weeks 16-20", "Ledger risk and backtesting", "Ledger, policy, backtest", "Each decision replays from evidence"],
  ["5", "Weeks 21-25", "Paper simulation", "Paper portfolios and copy shadowing", "Simulation audit trail, no live order path"],
  ["6", "Weeks 26-30", "Agents and evaluation", "Analysts, critic, drift, promotion gates", "Trace/eval suite and human promotion"],
  ["7", "Weeks 31-36", "Reliability and public beta", "Security, observability, documentation", "Load/recovery tests and v0.1 checklist"],
];

const wb = Workbook.create();
const overview = wb.worksheets.add("Overview");
const catalogue = wb.worksheets.add("Service catalogue");
const roadmap = wb.worksheets.add("Roadmap");
const readme = wb.worksheets.add("ReadMe");

for (const sheet of [overview, catalogue, roadmap, readme]) { sheet.showGridLines = false; }
overview.tabColor = navy; catalogue.tabColor = "#5B9BD5"; roadmap.tabColor = "#70AD47"; readme.tabColor = "#A5A5A5";

title(overview, "FinAgent Architecture Freeze", "H");
overview.getRange("A4:B9").values = [
  ["Architecture status", "Frozen - design only"],
  ["Scope", "Research, backtesting, paper trading, simulated copy trading"],
  ["Excluded", "Live execution, broker routing, custody, personalized investment advice"],
  ["Delivery horizon", "36 weeks / approximately 8-9 months"],
  ["Primary delivery shape", "Modular monolith first; extract services only when justified"],
  ["Core safety rule", "Risk gate and immutable ledger precede every simulation action"],
];
header(overview.getRange("A4:B4"));
body(overview.getRange("A5:B9"));
overview.getRange("A4:B4").values = [["Decision", "Frozen architecture"]];
overview.getRange("D4:E7").values = [
  ["Metric", "Value"],
  ["Logical components", `=COUNTA('Service catalogue'!A5:A22)`],
  ["Architecture phases", `=COUNTA(Roadmap!A5:A12)`],
  ["First delivery target", "Daily data -> baseline strategy -> ledger -> backtest -> evaluation"],
];
header(overview.getRange("D4:E4")); body(overview.getRange("D5:E7"));
overview.getRange("A12:H12").merge(); overview.getRange("A12").values = [["Core flow: source data -> quality -> point-in-time features -> research agents / quantitative models -> deterministic risk gate -> prediction ledger -> backtest or paper simulator -> evaluation -> governed promotion"]];
overview.getRange("A12").format = { fill: blue, font: { name: "Arial", size: 10, bold: true, color: "#1F1F1F" }, wrapText: true, verticalAlignment: "center", borders: { preset: "outside", style: "thin", color: grid } };
overview.getRange("A12").format.rowHeight = 42;
overview.getRange("A:A").format.columnWidth = 25; overview.getRange("B:B").format.columnWidth = 52; overview.getRange("D:D").format.columnWidth = 25; overview.getRange("E:E").format.columnWidth = 45;

title(catalogue, "FinAgent Service and Component Catalogue", "J");
const serviceHeaders = [["Component", "Domain", "Responsibility", "Technology", "Contract", "Owned records", "Primary storage", "Planned phase", "Deployment path", "Safety boundary"]];
catalogue.getRange("A4:J4").values = serviceHeaders; catalogue.getRange(`A5:J${4 + services.length}`).values = services;
header(catalogue.getRange("A4:J4")); body(catalogue.getRange(`A5:J${4 + services.length}`));
catalogue.tables.add(`A4:J${4 + services.length}`, true, "ServiceCatalogue");
catalogue.freezePanes.freezeRows(4);
const widths = [25, 14, 43, 31, 25, 29, 25, 16, 21, 35];
widths.forEach((w, i) => catalogue.getRangeByIndexes(0, i, 1, 1).format.columnWidth = w);
catalogue.getRange(`A5:J${4 + services.length}`).format.rowHeight = 38;

title(roadmap, "FinAgent 36 Week Roadmap", "E");
roadmap.getRange("A4:E4").values = [["Phase", "Schedule", "Theme", "Deliverable", "Exit criteria"]];
roadmap.getRange(`A5:E${4 + phases.length}`).values = phases;
header(roadmap.getRange("A4:E4")); body(roadmap.getRange(`A5:E${4 + phases.length}`));
roadmap.tables.add(`A4:E${4 + phases.length}`, true, "RoadmapTable");
roadmap.getRange("A15:E15").merge(); roadmap.getRange("A15").values = [["Actionable first 2-week plan"]];
roadmap.getRange("A15").format = { fill: blue, font: { name: "Arial", size: 11, bold: true }, verticalAlignment: "center" };
roadmap.getRange("A16:E21").values = [
  ["Week", "Focus", "Concrete action", "Proof", "Safety / quality check"],
  ["1", "Tooling", "Python workspace, formatting, types, tests, pre-commit", "Repeatable local command", "Secrets absent from repository"],
  ["1", "Contracts", "JSON Schema and OpenAPI skeleton", "Contract validation tests", "Versioned schemas"],
  ["1", "Data", "Fixture daily bars and normalized schema", "Manifest, checksum, timestamps", "Duplicate/out-of-order tests"],
  ["2", "Decision slice", "Baseline strategy, features, ledger, deterministic risk", "Ledger drilldown", "Reject missing provenance"],
  ["2", "Backtest", "Daily-bar simulation with declared costs and benchmark", "Run report", "Look-ahead bias tests"],
];
header(roadmap.getRange("A16:E16")); body(roadmap.getRange("A17:E21"));
roadmap.freezePanes.freezeRows(4);
[10, 17, 46, 34, 38].forEach((w, i) => roadmap.getRangeByIndexes(0, i, 1, 1).format.columnWidth = w);
roadmap.getRange("A5:E12").format.rowHeight = 38; roadmap.getRange("A17:E21").format.rowHeight = 36;

readme.getRange("A4:B10").values = [
  ["Sheet", "Purpose"],
  ["Overview", "Frozen architecture scope, safety boundaries, and live counts"],
  ["Service catalogue", "Editable logical components, responsibilities, technologies, contracts, timing, and safeguards"],
  ["Roadmap", "36-week phased delivery plan plus first two-week actions"],
  ["Documentation", "Markdown architecture documents in docs/architecture and docs/adr"],
  ["Editing guidance", "Update a component and its contract/ADR together; retain the paper-trading-only boundary"],
  ["Source", "FinAgent architecture freeze, 2026-09-12"],
];
header(readme.getRange("A4:B4")); body(readme.getRange("A5:B10"));
readme.getRange("A:A").format.columnWidth = 24; readme.getRange("B:B").format.columnWidth = 78; readme.getRange("A5:B10").format.rowHeight = 30;

wb.recalculate();
const check = await wb.inspect({ kind: "table", range: "Service catalogue!A4:J22", include: "values,formulas", tableMaxRows: 20, tableMaxCols: 10 });
const errors = await wb.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!", options: { useRegex: true, maxResults: 50 }, summary: "formula error scan" });
if (errors.ndjson && !errors.ndjson.includes("matched 0 entries")) throw new Error(`Formula errors: ${errors.ndjson}`);
await fs.mkdir(outDir, { recursive: true });
for (const [sheetName, range, file] of [
  ["Overview", "A1:H12", "overview-preview.png"],
  ["Service catalogue", "A1:J22", "service-catalogue-preview.png"],
  ["Roadmap", "A1:E21", "roadmap-preview.png"],
  ["ReadMe", "A1:B10", "readme-preview.png"],
]) {
  const preview = await wb.render({ sheetName, range, scale: 1.25, format: "png" });
  await fs.writeFile(`${outDir}/${file}`, new Uint8Array(await preview.arrayBuffer()));
}
const xlsx = await SpreadsheetFile.exportXlsx(wb);
await xlsx.save(outFile);
console.log(check.ndjson);
console.log(`Created ${outFile}`);
