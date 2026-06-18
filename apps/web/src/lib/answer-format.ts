export type AnswerBlock =
  | { type: "heading"; text: string; level: 2 | 3 }
  | { type: "paragraph"; text: string }
  | { type: "bullet_list"; items: string[] }
  | { type: "numbered_list"; items: string[] };

export function formatAnswerBlocks(content: string): AnswerBlock[] {
  const blocks: AnswerBlock[] = [];
  const lines = content.replace(/\r\n/g, "\n").split("\n");
  let paragraph: string[] = [];
  let bulletItems: string[] = [];
  let numberedItems: string[] = [];

  function flushParagraph() {
    if (paragraph.length > 0) {
      blocks.push({ type: "paragraph", text: paragraph.join(" ") });
      paragraph = [];
    }
  }

  function flushBulletList() {
    if (bulletItems.length > 0) {
      blocks.push({ type: "bullet_list", items: bulletItems });
      bulletItems = [];
    }
  }

  function flushNumberedList() {
    if (numberedItems.length > 0) {
      blocks.push({ type: "numbered_list", items: numberedItems });
      numberedItems = [];
    }
  }

  function flushLists() {
    flushBulletList();
    flushNumberedList();
  }

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) {
      flushParagraph();
      flushLists();
      continue;
    }

    const headingMatch = /^(#{2,3})\s+(.+)$/.exec(line);
    if (headingMatch) {
      flushParagraph();
      flushLists();
      blocks.push({
        type: "heading",
        level: headingMatch[1].length as 2 | 3,
        text: headingMatch[2],
      });
      continue;
    }

    const bulletMatch = /^[-*]\s+(.+)$/.exec(line);
    if (bulletMatch) {
      flushParagraph();
      flushNumberedList();
      bulletItems.push(bulletMatch[1]);
      continue;
    }

    const numberedMatch = /^\d+[.)]\s+(.+)$/.exec(line);
    if (numberedMatch) {
      flushParagraph();
      flushBulletList();
      numberedItems.push(numberedMatch[1]);
      continue;
    }

    flushLists();
    paragraph.push(line);
  }

  flushParagraph();
  flushLists();
  return blocks;
}
