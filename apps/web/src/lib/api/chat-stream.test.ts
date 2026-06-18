import { describe, expect, it } from "vitest";
import { parseSseChunk } from "./chat-stream";

describe("parseSseChunk", () => {
  it("parses multiple JSON data events from an SSE payload", () => {
    const events = parseSseChunk(
      'data: {"type":"status","content":"Checking workspace memory..."}\n\n' +
        'data: {"type":"answer_delta","content":"Ready"}\n\n',
    );

    expect(events).toEqual([
      { type: "status", content: "Checking workspace memory..." },
      { type: "answer_delta", content: "Ready" },
    ]);
  });

  it("returns a safe error event when a data event is malformed", () => {
    const events = parseSseChunk("data: {not-json}\n\n");

    expect(events).toEqual([
      {
        type: "error",
        content: "Received a streaming event that could not be parsed.",
      },
    ]);
  });
});
