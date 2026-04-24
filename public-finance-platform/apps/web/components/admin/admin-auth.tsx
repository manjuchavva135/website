"use client";

import Link from "next/link";
import React from "react";
import { createContext, useContext, useEffect, useState } from "react";
import type { AdminCredentials } from "@/lib/admin-api";

const STORAGE_KEY = "ap-finance-admin-credentials";

type AdminAuthContextValue = {
  credentials: AdminCredentials;
  signOut: () => void;
};

const AdminAuthContext = createContext<AdminAuthContextValue | null>(null);

export function useAdminAuth(): AdminAuthContextValue {
  const value = useContext(AdminAuthContext);
  if (!value) {
    throw new Error("useAdminAuth must be used inside AdminAuthProvider");
  }
  return value;
}

export function AdminAuthProvider({ children }: { children: React.ReactNode }) {
  const [credentials, setCredentials] = useState<AdminCredentials | null>(null);
  const [email, setEmail] = useState("");
  const [token, setToken] = useState("");
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw) {
      try {
        const parsed = JSON.parse(raw) as AdminCredentials;
        if (parsed.email && parsed.token) {
          setCredentials(parsed);
          setEmail(parsed.email);
        }
      } catch {
        window.localStorage.removeItem(STORAGE_KEY);
      }
    }
    setReady(true);
  }, []);

  function signIn(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const next = { email: email.trim(), token: token.trim() };
    setCredentials(next);
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  }

  function signOut() {
    setCredentials(null);
    setToken("");
    window.localStorage.removeItem(STORAGE_KEY);
  }

  if (!ready) {
    return (
      <section className="rounded-[2rem] border border-slate-200 bg-white/80 p-8 shadow-sm">
        <div className="h-8 w-64 animate-pulse rounded bg-slate-200" />
        <div className="mt-4 h-32 animate-pulse rounded-2xl bg-slate-100" />
      </section>
    );
  }

  if (!credentials) {
    return (
      <section className="mx-auto max-w-xl rounded-[2rem] border border-slate-200 bg-white/90 p-8 shadow-xl shadow-slate-200/60">
        <p className="text-xs font-bold uppercase tracking-[0.3em] text-teal-700">Admin access</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">
          Protected review workspace
        </h1>
        <p className="mt-3 text-sm leading-6 text-slate-600">
          Enter the admin email and token issued for the Andhra public-finance review workflow.
          The backend still authorizes every request.
        </p>
        <form className="mt-6 space-y-4" onSubmit={signIn}>
          <label className="block text-sm font-semibold text-slate-700">
            Admin email
            <input
              className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-teal-600 focus:ring-2 focus:ring-teal-100"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="admin@apfinance.local"
              required
            />
          </label>
          <label className="block text-sm font-semibold text-slate-700">
            Admin token
            <input
              className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-teal-600 focus:ring-2 focus:ring-teal-100"
              type="password"
              value={token}
              onChange={(event) => setToken(event.target.value)}
              placeholder="Shared admin token"
              required
            />
          </label>
          <button className="w-full rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white hover:bg-teal-800">
            Enter admin panel
          </button>
        </form>
      </section>
    );
  }

  return (
    <AdminAuthContext.Provider value={{ credentials, signOut }}>
      <div className="space-y-6">
        <div className="flex flex-col justify-between gap-4 rounded-[2rem] border border-slate-200 bg-slate-950 px-5 py-4 text-white shadow-xl shadow-slate-300/40 sm:flex-row sm:items-center">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.35em] text-teal-200">Admin panel</p>
            <p className="mt-1 text-sm text-slate-300">Signed in as {credentials.email}</p>
          </div>
          <div className="flex flex-wrap gap-2 text-sm">
            <Link className="rounded-full bg-white/10 px-4 py-2 hover:bg-white/20" href="/admin/review-queue">
              Review queue
            </Link>
            <Link className="rounded-full bg-white/10 px-4 py-2 hover:bg-white/20" href="/admin/releases">
              Releases
            </Link>
            <button className="rounded-full bg-white px-4 py-2 font-semibold text-slate-950" onClick={signOut}>
              Sign out
            </button>
          </div>
        </div>
        {children}
      </div>
    </AdminAuthContext.Provider>
  );
}
