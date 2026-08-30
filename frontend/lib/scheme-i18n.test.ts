import { describe, expect, it } from "vitest";

import { localizeScheme } from "@/lib/scheme-i18n";
import { seededSchemes } from "@/lib/seed-data";

describe("scheme localization", () => {
  it.each(["gu", "hi"] as const)("localizes every seeded scheme in %s", (language) => {
    for (const scheme of seededSchemes) {
      const localized = localizeScheme(scheme, language);
      expect(localized.name).not.toBe(scheme.name);
      expect(localized.benefitSummary).not.toBe(scheme.benefitSummary);
      expect(localized.rules[0].label).not.toBe(scheme.rules[0].label);
      expect(localized.documents[0].label).not.toBe(scheme.documents[0].label);
      expect(localized.sources).toEqual(scheme.sources);
    }
  });

  it("keeps the canonical English response unchanged", () => {
    expect(localizeScheme(seededSchemes[0], "en")).toBe(seededSchemes[0]);
  });
});
