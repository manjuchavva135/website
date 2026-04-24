import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AdminAuthProvider } from "./admin-auth";
import { AdminDocumentDetailView } from "./admin-document-detail";
import { AdminReleaseWorkspace } from "./admin-release-workspace";
import { AdminReviewDashboard } from "./admin-review-dashboard";

function renderWithAuth(ui: React.ReactNode) {
  return render(<AdminAuthProvider>{ui}</AdminAuthProvider>);
}

function signIn() {
  fireEvent.change(screen.getByLabelText(/Admin email/i), {
    target: { value: "admin@apfinance.local" },
  });
  fireEvent.change(screen.getByLabelText(/Admin token/i), {
    target: { value: "dev-admin-token" },
  });
  fireEvent.click(screen.getByRole("button", { name: /Enter admin panel/i }));
}

const documentList = {
  items: [
    {
      document_id: 10,
      source_name: "ap_finance",
      title: "Budget Summary 2026",
      parser_version: "2026.04.24",
      review_status: "pending",
      checksum_sha256: "a".repeat(64),
      created_at: "2026-04-24T10:00:00Z",
    },
  ],
  total: 1,
  page: 1,
  page_size: 100,
};

const documentDetail = {
  document_id: 10,
  source_name: "ap_finance",
  title: "Budget Summary 2026",
  review_status: "in_review",
  parser_version: "2026.04.24",
  rows: [
    {
      id: 1,
      page_number: 4,
      row_number: 12,
      row_label: "Revenue receipts",
      raw_text: "Revenue receipts | 1500",
      checksum_sha256: "b".repeat(64),
    },
  ],
  pages: [{ id: 1, page_number: 4, page_label: "4", row_start: 10, row_end: 18 }],
  parser_runs: [
    {
      id: 2,
      parser_name: "ap_parser",
      parser_version: "2026.04.24",
      status: "succeeded",
      rows_extracted: 1,
      warnings_count: 1,
      started_at: "2026-04-24T10:00:00Z",
      completed_at: "2026-04-24T10:01:00Z",
    },
  ],
  parser_errors: [
    {
      id: 3,
      error_level: "warning",
      error_code: "rounded",
      message: "Rounded value",
      row_number: 12,
      column_name: "amount",
      raw_value: "1499.995",
      created_at: "2026-04-24T10:01:00Z",
    },
  ],
  extracted_facts: [
    {
      target_table: "fiscal_metrics",
      target_id: 55,
      review_status: "pending",
      confidence_score: "0.9500",
      source_page_id: 1,
      page_number: 4,
      row_number: 12,
      row_label: "Revenue receipts",
      column_name: "amount",
      cell_ref: null,
      quoted_text: "Revenue receipts | 1500",
      notes: null,
    },
  ],
};

beforeEach(() => {
  window.localStorage.clear();
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const headers = init?.headers as Record<string, string>;
    if (headers?.["X-Admin-Email"] !== "admin@apfinance.local") {
      return new Response(JSON.stringify({ detail: "Missing admin credentials" }), { status: 401 });
    }
    if (url.includes("/documents/10/transition")) {
      return Response.json({ entity_table: "source_documents", entity_id: 10, state: "approved" });
    }
    if (url.includes("/facts/fiscal_metrics/55/decision")) {
      return Response.json({ entity_table: "fiscal_metrics", entity_id: 55, state: "approved" });
    }
    if (url.includes("/documents/10/rerun-parse")) {
      return Response.json({ parser_run_id: 99, task_name: "worker.tasks.ap", status: "pending" });
    }
    if (url.includes("/documents/10")) {
      return Response.json(documentDetail);
    }
    if (url.includes("/documents")) {
      return Response.json(documentList);
    }
    if (url.includes("/conflicts")) {
      return Response.json([
        {
          entity: "fiscal_metric",
          basis_tag: "audited_actual",
          left_source: "ap_finance",
          left_value: "100.00",
          right_source: "cag",
          right_value: "130.00",
          difference: "30.00",
          metric_code: "revenue_receipts",
          period_end: "2026-03-31",
          as_of_date: null,
        },
      ]);
    }
    if (url.includes("/reconciliation/7/annotate")) {
      return Response.json({ entity_table: "reconciliation_results", entity_id: 7, state: "annotated" });
    }
    if (url.includes("/releases/publish")) {
      return Response.json({
        id: 8,
        dataset_name: "andhra_public_finance",
        release_version: "v2026.04.24",
        status: "published",
        release_notes: "Approved release",
        manifest_checksum_sha256: "c".repeat(64),
        manifest_storage_key: "releases/manifest.json",
        published_at: "2026-04-24T11:00:00Z",
        created_at: "2026-04-24T11:00:00Z",
      });
    }
    if (url.includes("/releases/history")) {
      return Response.json([]);
    }
    return Response.json({});
  }));
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("admin review UI", () => {
  it("protects the queue and loads newly fetched documents after sign-in", async () => {
    renderWithAuth(<AdminReviewDashboard />);

    expect(document.body.textContent).toContain("Protected review workspace");
    signIn();

    expect(await screen.findByText("Budget Summary 2026")).toBeTruthy();
    expect(document.body.textContent).toContain("Conflicting official values");
    expect(document.body.textContent).toContain("Delta 30.00");
  });

  it("saves reconciliation notes from the dashboard", async () => {
    renderWithAuth(<AdminReviewDashboard />);
    signIn();

    await screen.findByText("Budget Summary 2026");
    fireEvent.change(screen.getByPlaceholderText("Result ID"), { target: { value: "7" } });
    fireEvent.change(screen.getByPlaceholderText(/Explain authoritative source/i), {
      target: { value: "CAG is authoritative" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Save note/i }));

    expect(await screen.findByText(/Reconciliation note saved/i)).toBeTruthy();
  });

  it("reviews facts and re-runs parsing from document detail", async () => {
    renderWithAuth(<AdminDocumentDetailView documentId={10} />);
    signIn();

    expect((await screen.findAllByText("Revenue receipts | 1500")).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Approve" }));
    expect(await screen.findByText(/Fact fiscal_metrics#55 approved/i)).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: /Re-run parse/i }));
    expect(await screen.findByText(/Parser re-run requested/i)).toBeTruthy();
  });

  it("previews and publishes dataset releases", async () => {
    renderWithAuth(<AdminReleaseWorkspace />);
    signIn();

    expect(await screen.findByText("Manifest and changelog preview")).toBeTruthy();
    fireEvent.change(screen.getByLabelText(/Release notes/i), {
      target: { value: "Approved release" },
    });
    fireEvent.change(screen.getByLabelText(/Changelog details/i), {
      target: { value: "Approved facts and manifest generated" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Publish immutable release/i }));

    await waitFor(() => {
      expect(document.body.textContent).toContain("Release v");
    });
  });
});
