import { describe, expect, it } from "vitest";
import { formatAnswerBlocks } from "./answer-format";

describe("formatAnswerBlocks", () => {
  it("groups headings, paragraphs, and lists into display blocks", () => {
    expect(
      formatAnswerBlocks(
        [
          "## Summary",
          "The rollout is ready",
          "after pricing copy is fixed.",
          "",
          "- Resolve pricing language",
          "- Assign rollback owner",
          "",
          "1. Ship limited beta",
          "2. Monitor usage",
        ].join("\n"),
      ),
    ).toEqual([
      { type: "heading", level: 2, text: "Summary" },
      { type: "paragraph", text: "The rollout is ready after pricing copy is fixed." },
      { type: "bullet_list", items: ["Resolve pricing language", "Assign rollback owner"] },
      { type: "numbered_list", items: ["Ship limited beta", "Monitor usage"] },
    ]);
  });
});
