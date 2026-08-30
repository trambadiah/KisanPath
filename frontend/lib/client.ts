import type {
  ApiErrorEnvelope,
  ConversationSnapshot,
  ConversationTurn,
  CreateConversationInput,
  EvaluationReport,
  KisanPathClient,
  LanguageCode,
  SchemeRecommendation,
} from "@/lib/contracts";
import { seededConversation, seededEvaluation, seededSchemes } from "@/lib/seed-data";

export class KisanPathApiError extends Error {
  constructor(
    message: string,
    readonly code: string,
    readonly retryable: boolean,
    readonly requestId: string,
  ) {
    super(message);
    this.name = "KisanPathApiError";
  }
}

function copy<T>(value: T): T {
  return structuredClone(value);
}

export class SeededKisanPathClient implements KisanPathClient {
  async createConversation(input: CreateConversationInput): Promise<ConversationSnapshot> {
    return { ...copy(seededConversation), language: input.preferredLanguage };
  }

  async getConversation(id: string): Promise<ConversationSnapshot> {
    return { ...copy(seededConversation), id };
  }

  async sendText(
    id: string,
    text: string,
    language: LanguageCode,
  ): Promise<ConversationTurn> {
    return this.demoTurn(id, text, language);
  }

  async sendAudio(
    id: string,
    _audio: Blob,
    language: LanguageCode,
  ): Promise<ConversationTurn> {
    const transcript = "મારી પાસે 3 એકર જમીન છે અને હું મગફળી ઉગાડું છું.";
    return {
      ...this.demoTurn(id, transcript, language),
      transcript: { text: transcript, language: "gu", confidence: 0.61 },
    };
  }

  async listRecommendations(conversationId: string): Promise<SchemeRecommendation[]> {
    void conversationId;
    return copy(seededSchemes);
  }

  async getScheme(id: string): Promise<SchemeRecommendation> {
    const scheme = seededSchemes.find((item) => item.id === id);
    if (!scheme) {
      throw new KisanPathApiError("Scheme not found.", "SCHEME_NOT_FOUND", false, "seeded");
    }
    return copy(scheme);
  }

  async getEvaluationReport(): Promise<EvaluationReport> {
    return copy(seededEvaluation);
  }

  private demoTurn(id: string, text: string, language: LanguageCode): ConversationTurn {
    const snapshot = copy(seededConversation);
    snapshot.id = id;
    snapshot.language = language;
    snapshot.stage = "CONFIRM_VALUE";
    snapshot.messages.push({
      id: `farmer-${Date.now()}`,
      role: "farmer",
      text,
      language,
      timestamp: new Intl.DateTimeFormat("en", {
        hour: "2-digit",
        minute: "2-digit",
      }).format(new Date()),
    });
    snapshot.pendingConfirmation = {
      fieldId: "land_area",
      label: "જમીનનો વિસ્તાર",
      heardValue: "3 એકર",
      alternatives: ["3 એકર", "30 એકર"],
      confidence: 0.61,
      source: "voice",
    };
    return {
      snapshot,
      responseText: {
        gu: "મેં જમીનનો વિસ્તાર 3 એકર સાંભળ્યો. શું તે સાચું છે?",
        hi: "मैंने भूमि क्षेत्र 3 एकड़ सुना। क्या यह सही है?",
        en: "I heard the land area as 3 acres. Is that correct?",
      }[language],
    };
  }
}

export class HttpKisanPathClient implements KisanPathClient {
  constructor(private readonly baseUrl: string) {}

  createConversation(input: CreateConversationInput): Promise<ConversationSnapshot> {
    return this.request("/v1/conversations", {
      method: "POST",
      body: JSON.stringify({
        preferred_language: input.preferredLanguage,
        client_capabilities: input.clientCapabilities,
      }),
    });
  }

  getConversation(id: string): Promise<ConversationSnapshot> {
    return this.request(`/v1/conversations/${encodeURIComponent(id)}`);
  }

  sendText(id: string, text: string, language: LanguageCode): Promise<ConversationTurn> {
    return this.request(`/v1/conversations/${encodeURIComponent(id)}/messages`, {
      method: "POST",
      body: JSON.stringify({ message_id: crypto.randomUUID(), text, language_hint: language }),
    });
  }

  sendAudio(id: string, audio: Blob, language: LanguageCode): Promise<ConversationTurn> {
    const body = new FormData();
    body.append("audio", audio, "farmer.webm");
    body.append("message_id", crypto.randomUUID());
    body.append("language_hint", language);
    return this.request(`/v1/conversations/${encodeURIComponent(id)}/audio`, {
      method: "POST",
      body,
    });
  }

  async listRecommendations(conversationId: string): Promise<SchemeRecommendation[]> {
    const snapshot = await this.getConversation(conversationId);
    return snapshot.recommendations;
  }

  getScheme(id: string): Promise<SchemeRecommendation> {
    return this.request(`/v1/schemes/${encodeURIComponent(id)}`);
  }

  getEvaluationReport(): Promise<EvaluationReport> {
    return this.request("/v1/eligibility/evaluate", {
      method: "POST",
      body: JSON.stringify({ dataset_id: "kisanpath-synthetic-seed", dataset_version: "1.0.0" }),
    });
  }

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const headers = new Headers(init.headers);
    if (typeof init.body === "string") headers.set("content-type", "application/json");
    const response = await fetch(`${this.baseUrl}${path}`, {
      ...init,
      headers,
      cache: "no-store",
    });
    if (!response.ok) {
      let envelope: ApiErrorEnvelope | undefined;
      try {
        envelope = (await response.json()) as ApiErrorEnvelope;
      } catch {
        envelope = undefined;
      }
      throw new KisanPathApiError(
        envelope?.error.message ?? "KisanPath is temporarily unavailable.",
        envelope?.error.code ?? "API_UNAVAILABLE",
        envelope?.error.retryable ?? response.status >= 500,
        envelope?.error.request_id ?? response.headers.get("x-request-id") ?? "unknown",
      );
    }
    return (await response.json()) as T;
  }
}

export function createKisanPathClient(): KisanPathClient {
  const apiBaseUrl = process.env.NEXT_PUBLIC_KISANPATH_API_URL?.replace(/\/$/, "");
  return apiBaseUrl ? new HttpKisanPathClient(apiBaseUrl) : new SeededKisanPathClient();
}
