import { readFile } from "node:fs/promises"
import { RuntimeState } from "./runtime-state"

// Invoked by the workspace synchronizer under its OS-level projection lock.
export async function importProjection(root: string, input: unknown, source: string) {
    if (!input || typeof input !== "object") throw new Error("Expected projection")
    const value = input as Record<string, unknown>
    for (const field of ["experiment_id", "run_id", "evidence_hash", "phase", "status", "conclusion"]) {
        if (typeof value[field] !== "string") throw new Error(`Invalid ${field}`)
    }
    const state = new RuntimeState(root, value.experiment_id as string)
    const content = JSON.stringify({ run_id: value.run_id, phase: value.phase, status: value.status,
        conclusion: value.conclusion, counts: value.counts, evidence_hash: value.evidence_hash,
        review_status: "unreviewed", source })
    const existing = (await state.snapshot()).memory.find(item => item.content === content)
    if (existing) return { created: false, id: existing.id }
    const entry = await state.remember(content, "note", [source])
    return { created: true, id: entry.id }
}

if (import.meta.main) {
    const [root, path] = process.argv.slice(2)
    if (!root || !path) throw new Error("Usage: sync-run.ts <state-root> <projection.json>")
    console.log(JSON.stringify(await importProjection(root, JSON.parse(await readFile(path, "utf8")), path)))
}
