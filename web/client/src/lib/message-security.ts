/**
 * Phoenix Lens local message analysis. It evaluates only text pasted by the user
 * and never sends text or follows detected links across the network.
 */
import { assessUrl, type LinkAssessment } from "@/lib/url-security";

export type LensSignal = {
  id: string;
  title: string;
  detail: string;
  points: number;
  source: "message" | "link";
};

export type LensAssessment = {
  score: number;
  band: "low" | "review" | "elevated" | "high";
  label: string;
  signals: LensSignal[];
  urls: string[];
  linkAssessment: LinkAssessment | null;
  steps: string[];
};

const URL_PATTERN = /(?:https?:\/\/|www\.)[^\s<>"']+/gi;

const CUES = [
  {
    id: "urgency",
    title: "لغة استعجال أو ضغط",
    detail: "تدفع الرسالة إلى التصرف بسرعة قبل التحقق المستقل من مصدرها.",
    points: 15,
    pattern: /(?:عاجل|فوراً|فورا|الآن|الان|خلال\s*\d+|آخر\s*فرصة|سيتم\s*(?:إيقاف|تعليق)|urgent|immediately|act now|final notice|suspended)/i,
  },
  {
    id: "credentials",
    title: "طلب بيانات اعتماد أو رمز تحقق",
    detail: "الجهات الموثوقة لا تطلب كلمة المرور أو رمز MFA عبر رسالة غير متوقعة.",
    points: 25,
    pattern: /(?:كلمة\s*المرور|رمز\s*(?:التحقق|التأكيد)|otp|mfa|verification\s*code|password|one[- ]time\s*code)/i,
  },
  {
    id: "financial",
    title: "طلب مالي أو بيانات دفع",
    detail: "توقف قبل مشاركة بيانات البطاقة أو تنفيذ تحويل من رابط وصل في رسالة.",
    points: 18,
    pattern: /(?:بطاق(?:ة|تك)|دفع|تحويل|حساب\s*بنكي|فاتورة|رسوم|payment|card|bank\s*account|transfer|invoice)/i,
  },
  {
    id: "impersonation",
    title: "ادعاء صفة جهة حساسة",
    detail: "تأكد من الجهة عبر موقعها أو رقمها المعروف، لا عبر تفاصيل الرسالة نفسها.",
    points: 11,
    pattern: /(?:بنك|مصرف|دعم\s*فني|شحن|جمارك|محفظة|bank|support|delivery|shipping|customs|wallet)/i,
  },
  {
    id: "attachment",
    title: "دعوة لتنزيل ملف أو فتح مرفق",
    detail: "لا تشغّل مرفقاً أو ملفاً قبل التحقق من المصدر وفحصه وفق سياسة جهازك.",
    points: 14,
    pattern: /(?:تحميل|نزّل|مرفق|ملف|download|attachment|install|open file)/i,
  },
];

function cleanUrl(url: string) {
  return url.replace(/[),.;!?]+$/, "");
}

function bandFor(score: number): Pick<LensAssessment, "band" | "label" | "steps"> {
  if (score >= 55) {
    return {
      band: "high",
      label: "أوقف التفاعل — إشارات عالية",
      steps: ["لا تفتح الرابط ولا ترد على الرسالة.", "اكتب موقع الجهة يدوياً أو اتصل برقم موثوق للتحقق.", "إن شاركت بيانات، غيّر كلمة المرور وألغِ الجلسات وفعّل MFA."],
    };
  }
  if (score >= 30) {
    return {
      band: "elevated",
      label: "تحقق مستقلاً قبل أي إجراء",
      steps: ["لا تدخل أي كلمة مرور أو رمز تحقق من الرسالة.", "تحقق من الجهة من قناة معروفة خارج النص.", "احتفظ بالرسالة كدليل وأبلغ الجهة عند التأكد."],
    };
  }
  if (score >= 12) {
    return {
      band: "review",
      label: "إشارات تحتاج مراجعة هادئة",
      steps: ["توقف لحظة وافحص السياق قبل النقر.", "تحقق من الرابط واسم النطاق بصورة مستقلة.", "لا تشارك أي معلومة حساسة حتى تتأكد من الجهة."],
    };
  }
  return {
    band: "low",
    label: "لا تظهر إشارات محلية قوية",
    steps: ["لا تعتبر النتيجة ضماناً للأمان.", "تحقق من المصدر عند أي طلب غير متوقع.", "حافظ على MFA وتحديثات جهازك مفعّلة."],
  };
}

export function assessMessage(text: string): LensAssessment {
  const normalized = text.trim();
  if (!normalized) throw new Error("ألصق نص رسالة أو رابطاً أولاً ليبدأ Phoenix Lens التحليل المحلي.");

  const signals: LensSignal[] = CUES.filter((cue) => cue.pattern.test(normalized)).map((cue) => ({
    id: cue.id,
    title: cue.title,
    detail: cue.detail,
    points: cue.points,
    source: "message",
  }));
  const urls = Array.from(normalized.matchAll(URL_PATTERN), (match) => cleanUrl(match[0]));
  let linkAssessment: LinkAssessment | null = null;

  if (urls.length) {
    signals.push({
      id: "link-present",
      title: "تحتوي الرسالة رابطاً",
      detail: "سيتم فحص بنية أول رابط محلياً؛ لم يتم فتح أي رابط أثناء التحليل.",
      points: 5,
      source: "link",
    });
    try {
      linkAssessment = assessUrl(urls[0]);
      signals.push(
        ...linkAssessment.signals.map((signal) => ({
          id: `link-${signal.id}`,
          title: `الرابط: ${signal.title}`,
          detail: signal.detail,
          points: signal.points,
          source: "link" as const,
        })),
      );
    } catch {
      signals.push({
        id: "malformed-link",
        title: "رابط غير قابل للقراءة",
        detail: "يتعذر تفسير بنية الرابط محلياً؛ لا تفتحه قبل التحقق من الجهة.",
        points: 14,
        source: "link",
      });
    }
  }

  const score = Math.min(100, signals.reduce((total, signal) => total + signal.points, 0));
  return { score, signals, urls, linkAssessment, ...bandFor(score) };
}
