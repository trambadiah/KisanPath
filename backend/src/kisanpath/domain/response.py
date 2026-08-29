"""Evidence-limited response planning and deterministic localization."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from kisanpath.domain.eligibility import SchemeEvaluation, SchemeStatus
from kisanpath.domain.profile import LanguageCode
from kisanpath.domain.scheme import Scheme
from kisanpath.domain.verification import ClaimVerificationBatch, VerificationStatus


class SchemeResponseItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    scheme_id: str = Field(min_length=1)
    scheme_name: str = Field(min_length=1)
    status: SchemeStatus
    missing_fields: tuple[str, ...] = ()
    source_ref_ids: tuple[str, ...] = Field(min_length=1)


class ResponsePlan(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    items: tuple[SchemeResponseItem, ...] = ()


class LocalizedResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    language: LanguageCode
    text: str = Field(min_length=1, max_length=20000)
    source_ref_ids: tuple[str, ...] = ()


class ResponseComposer:
    """Builds only claims whose overall verification is supported."""

    def compose(
        self,
        schemes: tuple[Scheme, ...],
        evaluations: tuple[SchemeEvaluation, ...],
        verifications: ClaimVerificationBatch,
    ) -> ResponsePlan:
        schemes_by_id = {scheme.scheme_id: scheme for scheme in schemes}
        evaluation_by_id = {evaluation.scheme_id: evaluation for evaluation in evaluations}
        items: list[SchemeResponseItem] = []
        for claim in verifications.claims:
            if not claim.claim_id.endswith(":overall"):
                continue
            if claim.status is not VerificationStatus.SUPPORTED:
                continue
            scheme_id = claim.claim_id.removesuffix(":overall")
            scheme = schemes_by_id.get(scheme_id)
            evaluation = evaluation_by_id.get(scheme_id)
            if scheme is None or evaluation is None or not claim.source_ref_ids:
                continue
            items.append(
                SchemeResponseItem(
                    scheme_id=scheme_id,
                    scheme_name=scheme.name,
                    status=evaluation.status,
                    missing_fields=evaluation.missing_fields,
                    source_ref_ids=claim.source_ref_ids,
                )
            )
        return ResponsePlan(items=tuple(items))


class ResponseLocalizer:
    """Conservative templates that cannot introduce new scheme facts."""

    _status = {
        LanguageCode.ENGLISH: {
            SchemeStatus.LIKELY_ELIGIBLE: "likely eligible based on the facts provided",
            SchemeStatus.NOT_ELIGIBLE: "not eligible under at least one published condition",
            SchemeStatus.INSUFFICIENT_INFORMATION: "needs more information",
            SchemeStatus.MANUAL_REVIEW: "requires manual review",
        },
        LanguageCode.HINDI: {
            SchemeStatus.LIKELY_ELIGIBLE: "दी गई जानकारी के आधार पर संभावित रूप से पात्र",
            SchemeStatus.NOT_ELIGIBLE: "कम-से-कम एक प्रकाशित शर्त के अनुसार पात्र नहीं",
            SchemeStatus.INSUFFICIENT_INFORMATION: "अधिक जानकारी आवश्यक",
            SchemeStatus.MANUAL_REVIEW: "मानवीय समीक्षा आवश्यक",
        },
        LanguageCode.GUJARATI: {
            SchemeStatus.LIKELY_ELIGIBLE: "આપેલી માહિતીના આધારે સંભવિત રીતે પાત્ર",
            SchemeStatus.NOT_ELIGIBLE: "ઓછામાં ઓછી એક પ્રકાશિત શરત મુજબ પાત્ર નથી",
            SchemeStatus.INSUFFICIENT_INFORMATION: "વધુ માહિતી જરૂરી",
            SchemeStatus.MANUAL_REVIEW: "માનવીય સમીક્ષા જરૂરી",
        },
    }
    _empty = {
        LanguageCode.ENGLISH: "I could not produce a verified scheme result.",
        LanguageCode.HINDI: "मैं सत्यापित योजना परिणाम तैयार नहीं कर सका।",
        LanguageCode.GUJARATI: "હું ચકાસાયેલ યોજના પરિણામ તૈયાર કરી શક્યો નથી.",
    }

    def localize(self, plan: ResponsePlan, language: LanguageCode) -> LocalizedResponse:
        resolved_language = (
            language if language is not LanguageCode.UNDETERMINED else LanguageCode.ENGLISH
        )
        if not plan.items:
            return LocalizedResponse(
                language=resolved_language,
                text=self._empty[resolved_language],
            )
        lines: list[str] = []
        citations: list[str] = []
        for item in plan.items:
            citation_text = ", ".join(item.source_ref_ids)
            lines.append(
                f"{item.scheme_name}: {self._status[resolved_language][item.status]} "
                f"[{citation_text}]"
            )
            citations.extend(item.source_ref_ids)
        return LocalizedResponse(
            language=resolved_language,
            text="\n".join(lines),
            source_ref_ids=tuple(dict.fromkeys(citations)),
        )

    def clarification(self, field: str, language: LanguageCode) -> str:
        resolved = language if language is not LanguageCode.UNDETERMINED else LanguageCode.ENGLISH
        labels = {
            "state": {
                LanguageCode.ENGLISH: "Which state is your farm in?",
                LanguageCode.HINDI: "आपका खेत किस राज्य में है?",
                LanguageCode.GUJARATI: "તમારું ખેતર કયા રાજ્યમાં છે?",
            },
            "district": {
                LanguageCode.ENGLISH: "Which district is your farm in?",
                LanguageCode.HINDI: "आपका खेत किस ज़िले में है?",
                LanguageCode.GUJARATI: "તમારું ખેતર કયા જિલ્લામાં છે?",
            },
            "land_area.normalized_hectares": {
                LanguageCode.ENGLISH: "What is your land area in acres or hectares?",
                LanguageCode.HINDI: "आपकी भूमि कितने एकड़ या हेक्टेयर है?",
                LanguageCode.GUJARATI: "તમારી જમીન કેટલા એકર અથવા હેક્ટર છે?",
            },
        }
        fallback = {
            LanguageCode.ENGLISH: f"Please provide the missing value for {field}.",
            LanguageCode.HINDI: f"कृपया {field} की जानकारी दें।",
            LanguageCode.GUJARATI: f"કૃપા કરીને {field} માટેની માહિતી આપો.",
        }
        return labels.get(field, fallback)[resolved]

    def confirmation(self, field: str, proposed_value: object, language: LanguageCode) -> str:
        resolved = language if language is not LanguageCode.UNDETERMINED else LanguageCode.ENGLISH
        templates = {
            LanguageCode.ENGLISH: "Please confirm {field}: {value}.",
            LanguageCode.HINDI: "कृपया {field} की पुष्टि करें: {value}।",
            LanguageCode.GUJARATI: "કૃપા કરીને {field}ની પુષ્ટિ કરો: {value}.",
        }
        return templates[resolved].format(field=field, value=proposed_value)
