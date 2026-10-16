import { test, expect } from "bun:test"
import { mkdtemp, rm } from "node:fs/promises"
import { tmpdir } from "node:os"
import { join } from "node:path"
import { importProjection } from "../src/sync-run"
import { RuntimeState } from "../src/runtime-state"

test("projection sync is idempotent and keeps negative evidence unreviewed", async () => {
    const root = await mkdtemp(join(tmpdir(), "projection-test-"))
    try {
        const input = { experiment_id: "example", run_id: "run-123", evidence_hash: "abc",
            phase: "confirmation", status: "completed", conclusion: "not_supported", counts: { pass: 12 } }
        expect((await importProjection(root, input, "source.json")).created).toBe(true)
        expect((await importProjection(root, input, "source.json")).created).toBe(false)
        const snapshot = await new RuntimeState(root, "example").snapshot()
        expect(snapshot.memory).toHaveLength(1)
        expect(JSON.parse(snapshot.memory[0].content).conclusion).toBe("not_supported")
        expect(JSON.parse(snapshot.memory[0].content).review_status).toBe("unreviewed")
        expect(snapshot.ideas).toHaveLength(0)
        await expect(importProjection(root, { experiment_id: "../escape" }, "source")).rejects.toThrow()
    } finally {
        await rm(root, { recursive: true, force: true })
    }
})
