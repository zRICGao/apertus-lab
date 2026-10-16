import { readFile } from "node:fs/promises"
import { RuntimeState } from "./runtime-state"

const [stateRoot, snapshotPath] = process.argv.slice(2)
if (!stateRoot || !snapshotPath) throw new Error("Usage: import-run.ts <state-directory> <run.json>")
const run: unknown = JSON.parse(await readFile(snapshotPath, "utf8"))
if (!run || typeof run !== "object") throw new Error("Expected a run snapshot")
const value = run as Record<string, unknown>
const spec = value.spec as Record<string, unknown> | undefined
if (!spec || typeof spec.id !== "string" || typeof value.run_id !== "string" ||
    typeof value.status !== "string" || !Array.isArray(value.attempts)) {
    throw new Error("Invalid run snapshot")
}
const state = new RuntimeState(stateRoot, spec.id)
// Runtime memory contains a summary only; the evidence ledger remains authoritative.
await state.remember(JSON.stringify({ run_id: value.run_id, status: value.status,
    phase: value.phase ?? "mock", attempts: value.attempts.length,
    review_status: "candidate", source: snapshotPath }), "note", [snapshotPath])
console.log(await state.board())
