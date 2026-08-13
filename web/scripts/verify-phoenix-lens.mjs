import { assessMessage } from "../client/src/lib/message-security.ts";

const ordinary = assessMessage("مرحباً، اجتماع الفريق غداً الساعة التاسعة في المكتب.");
if (ordinary.score !== 0 || ordinary.band !== "low" || ordinary.signals.length !== 0) {
  throw new Error("Expected ordinary text to have no local Phoenix Lens signals.");
}

const suspicious = assessMessage("عاجل: تم تعليق حسابك. افتح https://bit.ly/verify وأدخل كلمة المرور ورمز OTP الآن.");
const signalIds = new Set(suspicious.signals.map((signal) => signal.id));
for (const expected of ["urgency", "credentials", "link-present", "link-shortener"]) {
  if (!signalIds.has(expected)) throw new Error(`Expected Phoenix Lens signal not found: ${expected}`);
}
if (suspicious.band !== "high" || suspicious.score < 55) {
  throw new Error("Expected the compound phishing message to require a high review band.");
}

console.log("Phoenix Lens verification passed without network requests.");
