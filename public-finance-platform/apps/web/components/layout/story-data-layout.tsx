interface StoryDataLayoutProps {
  story: React.ReactNode;
  data: React.ReactNode;
}

/**
 * Standard page layout: Story section (chart + prose narrative) on top,
 * Data section (table + CSV download) below.
 */
export function StoryDataLayout({ story, data }: StoryDataLayoutProps) {
  return (
    <div className="space-y-8">
      <section>{story}</section>
      <section>
        <div className="mb-3 flex items-center gap-2">
          <div className="h-px flex-1 bg-slate-200" />
          <span className="text-[11px] font-semibold uppercase tracking-widest text-slate-400">
            Data
          </span>
          <div className="h-px flex-1 bg-slate-200" />
        </div>
        {data}
      </section>
    </div>
  );
}
