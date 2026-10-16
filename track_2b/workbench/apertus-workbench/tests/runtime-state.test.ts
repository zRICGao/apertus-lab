import { test, expect } from "bun:test"
import { mkdtemp, rm } from "node:fs/promises"
import { tmpdir } from "node:os"
import { join } from "node:path"
import { RuntimeState } from "../src/runtime-state"
import { UnconfiguredExperimentPort } from "../src/ports"

test("extracted state persists, deduplicates ideas and formats the board", async () => {
    const root = await mkdtemp(join(tmpdir(), "apertus-state-"))
    try {
        const state = new RuntimeState(root, "experiment-1")
        await state.remember("Observation | with a newline\nand source", "evidence", ["attempt-1"])
        await state.propose("Compare language variants")
        await state.propose("Compare language variants")
        const restored = new RuntimeState(root, "experiment-1")
        const snapshot = await restored.snapshot()
        expect(snapshot.memory[0].refs).toEqual(["attempt-1"])
        expect(snapshot.ideas).toHaveLength(1)
        expect(snapshot.ideas[0].status).toBe("pending")
        expect(await restored.board()).toContain("\\|")
        expect((await new RuntimeState(root, "experiment-2").snapshot()).memory).toHaveLength(0)
    } finally {
        await rm(root, { recursive: true, force: true })
    }
})

test("invalid scope and unconfigured transport fail explicitly", async () => {
    expect(() => new RuntimeState(".", "../escape")).toThrow()
    await expect(new UnconfiguredExperimentPort().test({
        experiment_id: "e", case_id: "c", target_id: "t",
    })).rejects.toThrow("not configured")
})
