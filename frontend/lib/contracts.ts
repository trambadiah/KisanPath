export type LanguageCode = "gu" | "hi" | "en";

export type EligibilityStatus =
  | "LIKELY_ELIGIBLE"
  | "NOT_ELIGIBLE"
  | "INSUFFICIENT_INFORMATION"
  | "MANUAL_REVIEW";

export type RuleResult = "PASS" | "FAIL" | "UNKNOWN" | "MANUAL_REVIEW";

export type VoiceState = "idle" | "listening" | "processing" | "speaking" | "error";

export interface ApiErrorEnvelope {
  error: {
    code: string;
    message: string;
    retryable: boolean;
    request_id: string;
  };
}

export interface ProfileFactView {
  id: string;
  label: string;
  value: string;
  status: "confirmed" | "needs_confirmation" | "missing";
  source: "voice" | "text" | "system";
  confidence?: number;
}

export interface EvidenceSource {
  id: string;
  title: string;
  publisher: string;
  locator: string;
  reviewedAt: string;
  excerpt: string;
  url?: string;
  status: "approved";
}

export interface EligibilityRuleView {
  id: string;
  label: string;
  result: RuleResult;
  explanation: string;
  sourceIds: string[];
}

export interface DocumentRequirement {
  id: string;
  label: string;
  detail: string;
  status: "ready" | "needed" | "check";
}

export interface SchemeRecommendation {
  id: string;
  name: string;
  shortName: string;
  status: EligibilityStatus;
  benefitSummary: string;
  fitReason: string;
  conditionsPassed: number;
  conditionsTotal: number;
  nextAction: string;
  rules: EligibilityRuleView[];
  documents: DocumentRequirement[];
  sources: EvidenceSource[];
  demo: boolean;
}

export interface ConversationMessage {
  id: string;
  role: "assistant" | "farmer";
  text: string;
  language: LanguageCode;
  timestamp: string;
}

export interface PendingConfirmationView {
  fieldId: string;
  label: string;
  heardValue: string;
  alternatives: string[];
  confidence: number;
  source: "voice";
}

export interface ConversationSnapshot {
  id: string;
  language: LanguageCode;
  stage:
    | "START"
    | "PARSE_INPUT"
    | "UPDATE_PROFILE"
    | "CONFIRM_VALUE"
    | "ASK_CLARIFICATION"
    | "DISCOVER_SCHEMES"
    | "EVALUATE_RULES"
    | "VERIFY_EVIDENCE"
    | "COMPOSE_RESPONSE"
    | "LOCALIZE"
    | "END";
  messages: ConversationMessage[];
  profile: ProfileFactView[];
  pendingConfirmation?: PendingConfirmationView;
  recommendations: SchemeRecommendation[];
}

export interface ConversationTurn {
  transcript?: {
    text: string;
    language: LanguageCode;
    confidence: number;
  };
  snapshot: ConversationSnapshot;
  responseText: string;
}

export interface MetricComparison {
  id: string;
  label: string;
  description: string;
  baseline: number;
  final: number;
  unit: "%" | "s";
  lowerIsBetter?: boolean;
}

export interface EvaluationCaseView {
  id: string;
  title: string;
  language: LanguageCode;
  input: string;
  expected: EligibilityStatus;
  actual: EligibilityStatus;
  passed: boolean;
  note: string;
}

export interface EvaluationReport {
  datasetVersion: string;
  generatedAt: string;
  syntheticOnly: boolean;
  metrics: MetricComparison[];
  cases: EvaluationCaseView[];
}

export interface CreateConversationInput {
  preferredLanguage: LanguageCode;
  clientCapabilities?: { audioInput: boolean; audioOutput: boolean };
}

export interface KisanPathClient {
  createConversation(input: CreateConversationInput): Promise<ConversationSnapshot>;
  getConversation(id: string): Promise<ConversationSnapshot>;
  sendText(id: string, text: string, language: LanguageCode): Promise<ConversationTurn>;
  sendAudio(id: string, audio: Blob, language: LanguageCode): Promise<ConversationTurn>;
  listRecommendations(conversationId: string): Promise<SchemeRecommendation[]>;
  getScheme(id: string): Promise<SchemeRecommendation>;
  getEvaluationReport(): Promise<EvaluationReport>;
}
