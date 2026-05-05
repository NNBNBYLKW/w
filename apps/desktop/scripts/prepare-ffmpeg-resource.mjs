import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const desktopDir = path.resolve(scriptDir, "..");
const outputDir = path.join(desktopDir, "build-resources", "ffmpeg");
const outputPath = path.join(outputDir, "ffmpeg.exe");
const ffmpegPath = require("ffmpeg-static");

if (!ffmpegPath || !fs.existsSync(ffmpegPath)) {
  throw new Error("ffmpeg-static did not resolve to an existing binary.");
}

fs.mkdirSync(outputDir, { recursive: true });
fs.copyFileSync(ffmpegPath, outputPath);
console.log(`Prepared bundled ffmpeg: ${outputPath}`);
