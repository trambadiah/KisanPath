"use client";

import { ArrowRight, Keyboard, LockKeyhole, Send, Signal, Sparkles, Volume2 } from "lucide-react";
import Link from "next/link";
import { FormEvent, useEffect, useRef, useState } from "react";

import { ConfirmationCard } from "@/components/confirmation-card";
import { useLocale } from "@/components/locale-provider";
import { ProfileChip } from "@/components/profile-chip";
import { ErrorState, LoadingState, OfflineNotice } from "@/components/state-panels";
import { VoiceOrb } from "@/components/voice-orb";
import type { ConversationSnapshot, VoiceState } from "@/lib/contracts";
import { createKisanPathClient } from "@/lib/client";
import { seededConversation } from "@/lib/seed-data";

export function AssistantExperience() {
  const clientRef = useRef(createKisanPathClient());
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const sessionStartedRef = useRef(false);
  const { language, t } = useLocale();
  const [snapshot, setSnapshot] = useState<ConversationSnapshot | null>(() =>
    process.env.NEXT_PUBLIC_KISANPATH_API_URL ? null : structuredClone(seededConversation),
  );
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [online, setOnline] = useState(true);
  const transcriptEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (sessionStartedRef.current) return;
    sessionStartedRef.current = true;
    clientRef.current
      .createConversation({ preferredLanguage: language, clientCapabilities: { audioInput: true, audioOutput: true } })
      .then(setSnapshot)
      .catch(() => setError(t("errorTitle")));
  }, [language, t]);

  useEffect(() => {
    const updateNetwork = () => setOnline(navigator.onLine);
    window.addEventListener("online", updateNetwork);
    window.addEventListener("offline", updateNetwork);
    updateNetwork();
    return () => {
      window.removeEventListener("online", updateNetwork);
      window.removeEventListener("offline", updateNetwork);
    };
  }, []);

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [snapshot?.messages.length]);

  async function handleVoicePress() {
    if (voiceState === "listening") {
      recorderRef.current?.stop();
      return;
    }
    if (!online) return;
    setError(null);
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setVoiceState("error");
      setError("Voice recording is not supported in this browser. You can continue by typing.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      streamRef.current = stream;
      recorderRef.current = recorder;
      chunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size) chunksRef.current.push(event.data);
      };
      recorder.onstop = async () => {
        streamRef.current?.getTracks().forEach((track) => track.stop());
        setVoiceState("processing");
        setBusy(true);
        try {
          const turn = await clientRef.current.sendAudio(
            snapshot?.id ?? "demo-conversation-001",
            new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" }),
            language,
          );
          turn.snapshot.messages.push({
            id: `assistant-${Date.now()}`,
            role: "assistant",
            text: turn.responseText,
            language,
            timestamp: "now",
          });
          setSnapshot(turn.snapshot);
          setVoiceState("idle");
        } catch {
          setVoiceState("error");
          setError("We could not process that recording. Your profile was not changed.");
        } finally {
          setBusy(false);
        }
      };
      recorder.start();
      setVoiceState("listening");
    } catch {
      setVoiceState("error");
      setError("Microphone access was not available. You can type the same message below.");
    }
  }

  async function submitText(event: FormEvent) {
    event.preventDefault();
    const text = draft.trim();
    if (!text || !online || busy) return;
    setDraft("");
    setBusy(true);
    setError(null);
    try {
      const turn = await clientRef.current.sendText(snapshot?.id ?? "demo-conversation-001", text, language);
      turn.snapshot.messages.push({
        id: `assistant-${Date.now()}`,
        role: "assistant",
        text: turn.responseText,
        language,
        timestamp: "now",
      });
      setSnapshot(turn.snapshot);
    } catch {
      setDraft(text);
      setError("Your message could not be sent. It remains in the text field so you can retry.");
    } finally {
      setBusy(false);
    }
  }

  async function confirmValue(value: string) {
    if (!snapshot) return;
    const updated = structuredClone(snapshot);
    updated.pendingConfirmation = undefined;
    updated.stage = "DISCOVER_SCHEMES";
    updated.profile = updated.profile.map((fact) =>
      fact.id === "land_area" ? { ...fact, value, status: "confirmed", confidence: 1 } : fact,
    );
    setSnapshot(updated);
    setBusy(true);
    await new Promise((resolve) => window.setTimeout(resolve, 700));
    updated.recommendations = await clientRef.current.listRecommendations(updated.id);
    updated.stage = "END";
    updated.messages.push({
      id: "results-ready",
      role: "assistant",
      text: t("resultsMessage"),
      language,
      timestamp: "now",
    });
    setSnapshot({ ...updated });
    setBusy(false);
  }

  if (!snapshot && !error) return <div className="assistantLoading"><LoadingState label={t("preparing")} /></div>;

  return (
    <main className="assistantMain">
      {!online && <OfflineNotice />}
      <section className="assistantIntro">
        <span className="eyebrow"><Signal size={13} />{t("privateSession")}</span>
        <h1>{t("assistantTitle")}</h1>
        <p>{t("assistantIntro")}</p>
      </section>

      <div className="assistantWorkspace">
        <section className="conversationPanel" aria-label={t("conversation")}>
          <div className="transcript" aria-live="polite" aria-relevant="additions">
            {snapshot?.messages.map((message) => (
              <div className={`messageRow message-${message.role}`} key={message.id}>
                <div className="messageMeta"><span>{message.role === "assistant" ? "KisanPath" : t("you")}</span><time>{message.timestamp}</time></div>
                <p lang={message.id === "welcome" ? language : message.language}>{message.id === "welcome" ? t("welcome") : message.text}</p>
              </div>
            ))}
            <div ref={transcriptEndRef} />
          </div>

          <div className="voiceStage">
            <VoiceOrb
              state={voiceState}
              onPress={handleVoicePress}
              caption={
                voiceState === "idle"
                  ? t("voiceIdle")
                  : voiceState === "listening"
                    ? t("voiceListening")
                    : voiceState === "processing"
                      ? t("voiceProcessing")
                      : voiceState === "speaking"
                        ? t("voiceSpeaking")
                        : t("voiceRetry")
              }
            />
          </div>

          {error && <ErrorState message={error} onRetry={() => { setError(null); setVoiceState("idle"); }} />}
          {busy && <LoadingState />}
          {snapshot?.pendingConfirmation && (
            <ConfirmationCard confirmation={snapshot.pendingConfirmation} onConfirm={confirmValue} onCorrect={() => document.getElementById("message-input")?.focus()} />
          )}
          {snapshot?.recommendations.length ? (
            <div className="resultsReadyCard">
              <div><span className="eyebrow"><Sparkles size={13} />{t("reviewComplete")}</span><strong>{t("matches", { count: snapshot.recommendations.length })}</strong><p>{t("resultsBody")}</p></div>
              <Link className="button buttonPrimary" href="/schemes">{t("viewResults")} <ArrowRight size={16} /></Link>
            </div>
          ) : null}

          <form className="messageComposer" onSubmit={submitText}>
            <Keyboard size={18} aria-hidden="true" />
            <label className="srOnly" htmlFor="message-input">{t("inputPlaceholder")}</label>
            <input id="message-input" value={draft} onChange={(event) => setDraft(event.target.value)} placeholder={t("inputPlaceholder")} disabled={!online || busy} />
            <button type="submit" aria-label={t("send")} disabled={!draft.trim() || !online || busy}><Send size={18} aria-hidden="true" /></button>
          </form>
          <p className="privacyLine"><LockKeyhole size={13} aria-hidden="true" />{t("sensitive")}</p>
        </section>

        <aside className="profileRail" aria-labelledby="profile-title">
          <div className="profileRailHeader"><div><span className="eyebrow">{t("decisionProfile")}</span><h2 id="profile-title">{t("relevantFacts")}</h2></div><span className="profileCount">{snapshot?.profile.filter((fact) => fact.status === "confirmed").length ?? 0}/{snapshot?.profile.length ?? 0}</span></div>
          <div className="profileChipStack">
            {snapshot?.profile.map((fact) => <ProfileChip key={fact.id} fact={fact} onEdit={() => document.getElementById("message-input")?.focus()} />)}
          </div>
          <div className="profileSafety"><Volume2 size={18} aria-hidden="true" /><p><strong>{t("voiceSourceTitle")}</strong>{t("voiceSourceBody")}</p></div>
        </aside>
      </div>
    </main>
  );
}
