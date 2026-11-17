// Run with Node 22.6+ (type stripping): node --experimental-strip-types --test tests/paperLibrary.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { filterPapers, selectionReason } from "../src/paperLibrary.ts";

const papers = Array.from({ length: 100 }, (_, i) => ({
  id: i + 1, title: `Paper ${String(i + 1).padStart(3, "0")}`,
  filename: `research-${i + 1}.pdf`, domain: i === 99 ? null : i % 2 ? "medicine" : "computing",
  page_count: 10, chunk_count: 20, status: "ready" as const, error_message: null,
  created_at: "2026-01-01T00:00:00Z",
}));

test("finds a paper among 100 by title or filename, ignoring case and outer spaces", () => {
  assert.deepEqual(filterPapers(papers, " PAPER 100 ", "", "newest").map(p => p.id), [100]);
  assert.deepEqual(filterPapers(papers, "research-42.PDF", "", "title").map(p => p.id), [42]);
  assert.equal(filterPapers(papers, "not found", "", "title").length, 0);
});
test("filters assigned/unassigned domains and sorts without mutating the library", () => {
  assert.equal(filterPapers(papers, "", "medicine", "newest").length, 49);
  assert.deepEqual(filterPapers(papers, "", "unassigned", "newest").map(p => p.id), [100]);
  assert.equal(filterPapers(papers, "", "", "newest")[0].id, 100);
  assert.equal(filterPapers(papers, "", "", "title")[0].id, 1);
  assert.equal(papers[0].id, 1);
});
test("comparison selection rejects missing or mismatched domains", () => {
  assert.equal(selectionReason(papers[99], papers, [], true), "unassigned");
  assert.equal(selectionReason(papers[1], papers, [1], true), "different_domain");
  assert.equal(selectionReason(papers[2], papers, [1], true), "");
  assert.equal(selectionReason(papers[1], papers, [1], false), "");
});
test("five-paper limit still permits removal and filtering leaves selection intact", () => {
  const selected = [1, 3, 5, 7, 9];
  assert.equal(selectionReason(papers[10], papers, selected, true), "limit");
  assert.equal(selectionReason(papers[0], papers, selected, true), "");
  filterPapers(papers, "Paper 100", "", "title");
  assert.deepEqual(selected, [1, 3, 5, 7, 9]);
});
