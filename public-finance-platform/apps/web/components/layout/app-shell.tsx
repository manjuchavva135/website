"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

// ─── Nav structure ─────────────────────────────────────────────────────────────

const NAV_GROUPS = [
  {
    label: "Overview",
    links: [
      { href: "/", label: "Home", icon: "🏛️" },
      { href: "/deficits", label: "Deficits", icon: "📊" },
    ],
  },
  {
    label: "Debt",
    links: [
      { href: "/debt-overview", label: "Debt Overview", icon: "💳" },
      { href: "/debt-issuance", label: "Debt Issuance", icon: "📤" },
      { href: "/debt-pipeline", label: "Debt Pipeline", icon: "🗓" },
      { href: "/repayments", label: "Repayments", icon: "↩" },
    ],
  },
  {
    label: "Fiscal",
    links: [
      { href: "/receipts", label: "Receipts", icon: "🧾" },
      { href: "/expenditure", label: "Expenditure", icon: "💰" },
      { href: "/department-spending", label: "Department Spending", icon: "🏢" },
    ],
  },
  {
    label: "Reference",
    links: [
      { href: "/sources", label: "Sources", icon: "📚" },
      { href: "/methodology", label: "Methodology", icon: "🔬" },
      { href: "/changelog", label: "Changelog", icon: "📝" },
      { href: "/api", label: "API", icon: "⚡" },
    ],
  },
  {
    label: "Admin",
    links: [
      { href: "/admin/review-queue", label: "Review Queue", icon: "A" },
      { href: "/admin/releases", label: "Releases", icon: "R" },
    ],
  },
];

// ─── Shared NavContent ────────────────────────────────────────────────────────

function NavContent({
  pathname,
  onLinkClick,
}: {
  pathname: string;
  onLinkClick?: () => void;
}) {
  return (
    <nav aria-label="Main navigation" className="flex flex-col gap-1 px-3 py-4">
      {NAV_GROUPS.map((group) => (
        <div key={group.label} className="mb-2">
          <p className="mb-1 px-2 text-[10px] font-bold uppercase tracking-widest text-slate-400">
            {group.label}
          </p>
          {group.links.map(({ href, label, icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                onClick={onLinkClick}
                className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  active
                    ? "bg-tide/10 text-tide"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`}
                aria-current={active ? "page" : undefined}
              >
                <span aria-hidden="true">{icon}</span>
                {label}
              </Link>
            );
          })}
        </div>
      ))}
    </nav>
  );
}

// ─── App Shell ────────────────────────────────────────────────────────────────

export function AppShell({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const pathname = usePathname();

  return (
    <div className="flex min-h-screen">
      {/* ── Desktop sidebar ─────────────────────────────────────────────── */}
      <aside className="hidden w-56 shrink-0 border-r border-slate-200 bg-white/90 backdrop-blur lg:flex lg:flex-col">
        <div className="border-b border-slate-100 px-4 py-4">
          <Link href="/" className="block">
            <p className="text-xs font-bold uppercase tracking-widest text-tide">
              AP Finance
            </p>
            <p className="mt-0.5 text-[11px] text-slate-400">Transparency Platform</p>
          </Link>
        </div>
        <div className="flex-1 overflow-y-auto">
          <NavContent pathname={pathname} />
        </div>
      </aside>

      {/* ── Mobile overlay ───────────────────────────────────────────────── */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-ink/30 backdrop-blur-sm lg:hidden"
          onClick={() => setMobileOpen(false)}
          aria-hidden="true"
        />
      )}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 border-r border-slate-200 bg-white shadow-xl transition-transform lg:hidden ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
        aria-label="Mobile navigation"
      >
        <div className="flex items-center justify-between border-b border-slate-100 px-4 py-4">
          <Link href="/" onClick={() => setMobileOpen(false)}>
            <p className="text-xs font-bold uppercase tracking-widest text-tide">
              AP Finance
            </p>
          </Link>
          <button
            onClick={() => setMobileOpen(false)}
            className="rounded-md p-1 text-slate-500 hover:bg-slate-100"
            aria-label="Close menu"
          >
            ✕
          </button>
        </div>
        <div className="overflow-y-auto pb-8">
          <NavContent pathname={pathname} onLinkClick={() => setMobileOpen(false)} />
        </div>
      </aside>

      {/* ── Main content ─────────────────────────────────────────────────── */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Mobile top bar */}
        <header className="sticky top-0 z-30 flex items-center justify-between border-b border-slate-200 bg-white/90 px-4 py-3 backdrop-blur lg:hidden">
          <button
            onClick={() => setMobileOpen(true)}
            className="rounded-md p-1.5 text-slate-600 hover:bg-slate-100"
            aria-label="Open menu"
            aria-expanded={mobileOpen}
          >
            ☰
          </button>
          <Link href="/">
            <span className="text-sm font-bold tracking-wide text-tide">AP Finance</span>
          </Link>
          <div className="w-8" /> {/* spacer */}
        </header>

        <main className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6">
          {children}
        </main>
      </div>
    </div>
  );
}
