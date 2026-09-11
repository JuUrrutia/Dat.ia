import React from 'react';

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
        <strong key={part.id} className="text-white font-semibold">
          {part.content.slice(2, -2)}
        </strong>
      );
    }
    if (part.content.startsWith('`') && part.content.endsWith('`')) {
      return (
        <code key={part.id} className="bg-dark-base px-1.5 py-0.5 rounded text-cyan-300 font-mono text-xs border border-dark-border">
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
      <div className="text-xs sm:text-sm text-gray-200 leading-relaxed whitespace-pre-wrap font-sans">
        {rawContent}
      </div>
    );
  }

  return (
    <div className="space-y-3 sm:space-y-4 font-sans text-xs sm:text-sm text-gray-200">
      {parsedSections.map((sec) => {
        if (sec.type === 'h2') {
          return (
            <div key={sec.id} className="pb-2 border-b border-dark-border/80 flex items-center space-x-2 pt-2">
              <span className="w-2 h-2 rounded-full bg-cyan-400" />
              <h3 className="text-sm sm:text-base font-extrabold text-white tracking-tight">
                {sec.content}
              </h3>
            </div>
          );
        }

        if (sec.type === 'h3') {
          return (
            <div
              key={sec.id}
              className="flex items-center space-x-2.5 pt-2 mt-3 first:mt-0"
            >
              {sec.number !== undefined ? (
                <div className="w-5 h-5 rounded-md bg-brand-500/20 text-brand-300 font-bold flex items-center justify-center text-xs shrink-0 border border-brand-500/30">
                  {sec.number}
                </div>
              ) : (
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
              )}
              <h4 className="text-xs sm:text-sm font-bold text-gray-100 tracking-tight">
                {sec.content}
              </h4>
            </div>
          );
        }

        if (sec.type === 'callout') {
          return (
            <blockquote
              key={sec.id}
              className="border-l-2 border-cyan-400 bg-cyan-500/5 px-3.5 py-2 rounded-r-xl text-xs text-gray-300 leading-relaxed italic my-2"
            >
              {formatInlineMarkdown(sec.content, sec.id)}
            </blockquote>
          );
        }

        if (sec.type === 'bullet') {
          return (
            <div
              key={sec.id}
              className="flex items-start space-x-2 text-xs sm:text-sm text-gray-300 leading-relaxed pl-1 py-0.5"
            >
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 mt-2 shrink-0" />
              <div className="leading-relaxed font-normal flex-1">
                {formatInlineMarkdown(sec.content, sec.id)}
              </div>
            </div>
          );
        }

        return (
          <p
            key={sec.id}
            className="text-xs sm:text-sm text-gray-200 leading-relaxed font-normal my-1"
          >
            {formatInlineMarkdown(sec.content, sec.id)}
          </p>
        );
      })}
    </div>
  );
};
