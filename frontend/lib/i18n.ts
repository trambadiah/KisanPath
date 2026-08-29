import type { LanguageCode } from "@/lib/contracts";

export const languageNames: Record<LanguageCode, string> = {
  gu: "ગુજરાતી",
  hi: "हिन्दी",
  en: "English",
};

export const assistantCopy: Record<
  LanguageCode,
  {
    title: string;
    voiceIdle: string;
    voiceListening: string;
    voiceProcessing: string;
    voiceSpeaking: string;
    inputPlaceholder: string;
    send: string;
  }
> = {
  gu: {
    title: "તમારી ખેતી માટે યોગ્ય સહાય શોધીએ",
    voiceIdle: "બોલવા માટે ટેપ કરો",
    voiceListening: "હું સાંભળી રહ્યો છું…",
    voiceProcessing: "તમારી વાત સમજી રહ્યો છું…",
    voiceSpeaking: "જવાબ વાંચી રહ્યો છું…",
    inputPlaceholder: "અથવા અહીં લખો…",
    send: "મોકલો",
  },
  hi: {
    title: "आपकी खेती के लिए सही सहायता खोजें",
    voiceIdle: "बोलने के लिए टैप करें",
    voiceListening: "मैं सुन रहा हूँ…",
    voiceProcessing: "आपकी बात समझ रहा हूँ…",
    voiceSpeaking: "जवाब पढ़ रहा हूँ…",
    inputPlaceholder: "या यहाँ लिखें…",
    send: "भेजें",
  },
  en: {
    title: "Find the right support for your farm",
    voiceIdle: "Tap to speak",
    voiceListening: "I’m listening…",
    voiceProcessing: "Understanding your request…",
    voiceSpeaking: "Reading the response…",
    inputPlaceholder: "Or type here…",
    send: "Send",
  },
};
