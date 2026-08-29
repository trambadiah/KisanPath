import { afterEach, describe, expect, it, vi } from "vitest";

import { HttpKisanPathClient, KisanPathApiError, SeededKisanPathClient } from "@/lib/client";
import { seededConversation, seededEvaluation } from "@/lib/seed-data";

afterEach(() => vi.unstubAllGlobals());

describe("SeededKisanPathClient", () => {
  it("keeps demo data behind the production client contract", async () => {
    const client = new SeededKisanPathClient();
    const schemes = await client.listRecommendations("demo-conversation");

    expect(schemes).toHaveLength(3);
    expect(schemes.every((scheme) => scheme.demo)).toBe(true);
    expect(schemes.every((scheme) => scheme.sources.length > 0)).toBe(true);
    expect(schemes.flatMap((scheme) => scheme.rules).every((rule) => rule.sourceIds.length > 0)).toBe(
      true,
    );
  });

  it("returns ASR confidence and alternatives for the critical land value", async () => {
    const client = new SeededKisanPathClient();
    const turn = await client.sendAudio("conversation", new Blob(["audio"]), "gu");

    expect(turn.transcript?.confidence).toBe(0.61);
    expect(turn.snapshot.stage).toBe("CONFIRM_VALUE");
    expect(turn.snapshot.pendingConfirmation?.alternatives).toEqual(["3 એકર", "30 એકર"]);
  });

  it("normalizes unknown seeded scheme IDs", async () => {
    const client = new SeededKisanPathClient();

    await expect(client.getScheme("missing")).rejects.toBeInstanceOf(KisanPathApiError);
  });

  it("uses the versioned conversation and evaluation API contracts", async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ...seededConversation, recommendations: [] }), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(seededEvaluation), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      );
    vi.stubGlobal("fetch", fetchMock);
    const client = new HttpKisanPathClient("https://api.example.test");

    await client.listRecommendations("conversation/one");
    await client.getEvaluationReport();

    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      "https://api.example.test/v1/conversations/conversation%2Fone",
    );
    expect(fetchMock.mock.calls[1]?.[0]).toBe(
      "https://api.example.test/v1/eligibility/evaluate",
    );
    expect(fetchMock.mock.calls[1]?.[1]?.method).toBe("POST");
  });
});
