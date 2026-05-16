export function suggestCollectionName(paths: string[]): string {
  if (paths.length === 0) return "Collection";
  const stems = paths.map(p => {
    const base = p.replace(/\\/g, "/").split("/").pop() || p;
    const dot = base.lastIndexOf(".");
    const stem = dot > 0 ? base.substring(0, dot) : base;
    return stem.replace(/[_\-.\s]+/g, " ").trim();
  }).filter(s => s.length > 0);
  if (stems.length === 0) {
    const now = new Date();
    return `Collection ${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,"0")}-${String(now.getDate()).padStart(2,"0")} ${String(now.getHours()).padStart(2,"0")}${String(now.getMinutes()).padStart(2,"0")}`;
  }
  let prefix = stems[0];
  for (let i = 1; i < stems.length; i++) {
    while (prefix && !stems[i].toLowerCase().startsWith(prefix.toLowerCase())) {
      prefix = prefix.substring(0, prefix.length - 1).trimEnd();
    }
  }
  prefix = prefix.replace(/\s+(S?\d{1,2}[Ee]\d{1,3}|EP?\d{2,3}|Lesson\s*\d{2,3}|Part\s*\d{2,3}|Chapter\s*\d{2,3}|\d{2,4})\s*$/i, "").trim();
  prefix = prefix.replace(/\s+\d*\s*$/, "").trim();
  const generic = new Set(["img", "dsc", "vid", "dscn", "pict", "mov", "clip", "img_", "dsc_"]);
  if (prefix.length < 3 || generic.has(prefix.toLowerCase()) || !prefix) {
    const now = new Date();
    return `Collection ${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,"0")}-${String(now.getDate()).padStart(2,"0")} ${String(now.getHours()).padStart(2,"0")}${String(now.getMinutes()).padStart(2,"0")}`;
  }
  return prefix;
}

export function suggestTypeForFiles(files: { name: string }[]): string {
  if (files.length === 0) return "";
  const exts = new Set(files.map(f => {
    const base = f.name.replace(/\\/g, "/").split("/").pop() || "";
    const dot = base.lastIndexOf(".");
    return dot > 0 ? base.substring(dot + 1).toLowerCase() : "";
  }).filter(e => e));
  const v = new Set(["mp4","mkv","avi","mov","webm","wmv","m4v","mpg","mpeg"]);
  const i = new Set(["jpg","jpeg","png","gif","bmp","webp","tiff","tif"]);
  const a = new Set(["mp3","wav","flac","ogg","m4a","aac","opus"]);
  const d = new Set(["pdf","doc","docx","ppt","pptx","xls","xlsx","txt","md","rtf"]);
  const vc = [...exts].filter(e => v.has(e)).length;
  const ic = [...exts].filter(e => i.has(e)).length;
  const ac = [...exts].filter(e => a.has(e)).length;
  const dc = [...exts].filter(e => d.has(e)).length;
  if (vc > 0 && ic + ac + dc === 0) return "video_collection";
  if (vc > 0 && dc > 0) return "course";
  if (ic > 0 && vc + ac === 0) return "imgset";
  if (ac > 0 && vc + ic === 0) return "audio";
  return "";
}
