import { describe, expect, it } from "vitest";

import { translate } from "@/lib/i18n";

describe("translation catalog", () => {
  it("translates representative navigation and page content in Gujarati and Hindi", () => {
    expect(translate("gu", "recommendations")).toBe("ભલામણો");
    expect(translate("hi", "recommendations")).toBe("सिफारिशें");
    expect(translate("gu", "heroTitle")).not.toBe(translate("en", "heroTitle"));
    expect(translate("hi", "privacyTitle")).not.toBe(translate("en", "privacyTitle"));
  });

  it("interpolates translated messages without leaving placeholders", () => {
    expect(translate("gu", "matches", { count: 3 })).toContain("3");
    expect(translate("hi", "matches", { count: 3 })).not.toContain("{count}");
  });
});
