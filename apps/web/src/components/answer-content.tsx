import { formatAnswerBlocks } from "@/lib/answer-format";
import { cn } from "@/lib/utils";

type AnswerContentProps = {
  content: string;
  className?: string;
};

function renderInlineText(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={`${part}-${index}`} className="font-semibold text-[#111111]">
          {part.slice(2, -2)}
        </strong>
      );
    }
    return part;
  });
}

export function AnswerContent({ content, className }: AnswerContentProps) {
  const blocks = formatAnswerBlocks(content);

  if (blocks.length === 0) {
    return null;
  }

  return (
    <div className={cn("space-y-3 text-[14px] leading-6 text-[#202020]", className)}>
      {blocks.map((block, index) => {
        if (block.type === "heading") {
          const HeadingTag = block.level === 2 ? "h3" : "h4";
          return (
            <HeadingTag
              key={`${block.type}-${index}`}
              className="pt-1 text-[15px] font-semibold leading-6 text-[#111111]"
            >
              {renderInlineText(block.text)}
            </HeadingTag>
          );
        }

        if (block.type === "bullet_list") {
          return (
            <ul key={`${block.type}-${index}`} className="space-y-1.5 pl-4">
              {block.items.map((item, itemIndex) => (
                <li key={`${item}-${itemIndex}`} className="list-disc pl-1">
                  {renderInlineText(item)}
                </li>
              ))}
            </ul>
          );
        }

        if (block.type === "numbered_list") {
          return (
            <ol key={`${block.type}-${index}`} className="space-y-1.5 pl-4">
              {block.items.map((item, itemIndex) => (
                <li key={`${item}-${itemIndex}`} className="list-decimal pl-1">
                  {renderInlineText(item)}
                </li>
              ))}
            </ol>
          );
        }

        return (
          <p key={`${block.type}-${index}`} className="whitespace-pre-wrap">
            {renderInlineText(block.text)}
          </p>
        );
      })}
    </div>
  );
}
