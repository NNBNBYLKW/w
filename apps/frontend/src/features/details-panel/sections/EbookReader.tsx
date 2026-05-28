import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

interface EpubContent {
  title?: string | null;
  author?: string | null;
  chapters: Array<{ title: string; text: string }>;
}

export function EbookReader({ fileId }: { fileId: number }) {
  const [chapterIdx, setChapterIdx] = useState(0);
  const { data } = useQuery({
    queryKey: ["epub", fileId],
    queryFn: async () => {
      const r = await fetch(`http://127.0.0.1:8000/files/${fileId}/epub-content`);
      const json = await r.json();
      return json.item as EpubContent;
    },
  });
  if (!data) return <p>Loading...</p>;
  const chapter = data.chapters?.[chapterIdx];
  return (
    <div className="ebook-reader">
      <h3>{data.title ?? "Unknown"}</h3>
      {data.author && <p className="ebook-reader__author">{data.author}</p>}
      <select value={chapterIdx} onChange={e => setChapterIdx(Number(e.target.value))}>
        {data.chapters.map((ch, i) => <option key={i} value={i}>{ch.title}</option>)}
      </select>
      <div className="ebook-reader__content">{chapter?.text}</div>
      <div className="ebook-reader__nav">
        <button onClick={() => setChapterIdx(i => Math.max(0, i - 1))} disabled={chapterIdx === 0}>Prev</button>
        <button onClick={() => setChapterIdx(i => Math.min(data.chapters.length - 1, i + 1))} disabled={chapterIdx >= data.chapters.length - 1}>Next</button>
      </div>
    </div>
  );
}
