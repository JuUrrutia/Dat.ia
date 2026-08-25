import React from 'react';

// Helper to parse sections/ideas from markdown
export const parseMarkdownContent = (text: string) => {
  const lines = text.split('\n');
  const sections: Array<{
    id: string;
    type: 'h2' | 'h3' | 'callout' | 'bullet' | 'paragraph';
    content: string;
    number?: number;
  }> = [];

  let currentParagraph = '';

  const addSection = (
    type: 'h2' | 'h3' | 'callout' | 'bullet' | 'paragraph',
    content: string,
    number?: number
  ) => {
    const id = `sec-${sections.length}-${type}`;
    sections.push({
      id,
      type,
      content,
      ...(number !== undefined ? { number } : {}),
    });
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

    if (line.startsWith('## ')) {
      if (currentParagraph) {
        addSection('paragraph', currentParagraph);
        currentParagraph = '';
      }
      addSection('h2', line.replace(/^##\s+/, ''));
    } else if (line.startsWith('### ')) {
      if (currentParagraph) {
        addSection('paragraph', currentParagraph);
        currentParagraph = '';
      }
      const h3Text = line.replace(/^###\s+/, '');
      const numMatch = h3Text.match(/^(\d+)[.\s-]+(.*)/);
      if (numMatch) {
        addSection('h3', numMatch[2].trim(), parseInt(numMatch[1], 10));
      } else {
        addSection('h3', h3Text);
      }
    } else if (line.startsWith('> ')) {
      if (currentParagraph) {
        addSection('paragraph', currentParagraph);
        currentParagraph = '';
      }
      addSection('callout', line.replace(/^>\s+/, ''));
    } else if (line.startsWith('* ') || line.startsWith('- ')) {
      if (currentParagraph) {
        addSection('paragraph', currentParagraph);
        currentParagraph = '';
      }
      addSection('bullet', line.replace(/^[\*\-]\s+/, ''));
    } else if (line === '') {
      if (currentParagraph) {
        addSection('paragraph', currentParagraph);
        currentParagraph = '';
      }
    } else {
      currentParagraph = currentParagraph ? `${currentParagraph} ${line}` : line;
    }
  }

  if (currentParagraph) {
    addSection('paragraph', currentParagraph);
  }

  return sections;
};

export const formatInlineMarkdown = (text: string, keyPrefix: string = 'inline') => {
  const rawParts = text.split(/(\*\*.*?\*\*|`.*?`)/g);
  let counter = 0;
  const parts = rawParts.map((content) => {
    counter += 1;
    return {
      id: `${keyPrefix}-part-${counter}`,
      content,
    };
  });

  return parts.map((part) => {
    if (part.content.startsWith('**') && part.content.endsWith('**')) {
      return (
        <strong key={part.id} className="text-amber-300 font-semibold">
          {part.content.slice(2, -2)}
        </strong>
      );
    }
    if (part.content.startsWith('`') && part.content.endsWith('`')) {
      return (
        <code key={part.id} className="bg-zinc-950 px-1.5 py-0.5 rounded text-amber-300 font-mono text-xs border border-white/10">
          {part.content.slice(1, -1)}
        </code>
      );
    }
    return part.content;
  });
};

interface AssistantMarkdownBodyProps {
  rawContent: string;
}

export const AssistantMarkdownBody: React.FC<AssistantMarkdownBodyProps> = ({ rawContent }) => {
  const parsedSections = parseMarkdownContent(rawContent);

  if (parsedSections.length === 0) {
    return (
      <div className="text-sm text-zinc-200 leading-relaxed whitespace-pre-wrap">
        {rawContent}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {parsedSections.map((sec) => {
        if (sec.type === 'h2') {
          return (
            <div key={sec.id} className="pb-3 border-b border-white/10 flex items-center space-x-2.5">
              <div className="w-2 h-2 rounded-full bg-amber-400" />
              <h3 className="text-base font-bold text-white tracking-tight">
                {sec.content}
              </h3>
            </div>
          );
        }

        if (sec.type === 'h3') {
          return (
            <div
              key={sec.id}
              className="flex items-center space-x-3 pt-2 mt-4 first:mt-0"
            >
              {sec.number !== undefined ? (
                <div className="w-6 h-6 rounded-lg bg-amber-500/20 text-amber-300 font-extrabold flex items-center justify-center text-xs shrink-0 border border-amber-500/30 shadow-md shadow-amber-500/10">
                  {sec.number}
                </div>
              ) : (
                <div className="w-2 h-2 rounded-full bg-amber-400" />
              )}
              <h4 className="text-sm font-bold text-amber-300/95 tracking-tight">
                {sec.content}
              </h4>
            </div>
          );
        }

        if (sec.type === 'callout') {
          return (
            <blockquote
              key={sec.id}
              className="border-l-2 border-amber-400/80 bg-amber-500/5 px-4 py-2.5 rounded-r-xl text-xs text-amber-200/90 leading-relaxed italic my-2"
            >
              {formatInlineMarkdown(sec.content, sec.id)}
            </blockquote>
          );
        }

        if (sec.type === 'bullet') {
          return (
            <div
              key={sec.id}
              className="flex items-start space-x-2.5 text-sm text-zinc-300 leading-relaxed pl-1 py-0.5"
            >
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400 mt-2 shrink-0" />
              <div className="leading-relaxed font-normal flex-1">
                {formatInlineMarkdown(sec.content, sec.id)}
              </div>
            </div>
          );
        }

        return (
          <p
            key={sec.id}
            className="text-sm text-zinc-200 leading-relaxed font-normal my-1"
          >
            {formatInlineMarkdown(sec.content, sec.id)}
          </p>
        );
      })}
    </div>
  );
};
