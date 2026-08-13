/** Local, non-network URL risk heuristics for the Phoenix defensive inspector. */

export type LinkSignal = {
  id: string;
  title: string;
  detail: string;
  points: number;
};

export type LinkAssessment = {
  normalized: string;
  host: string;
  protocol: string;
  score: number;
  band: "low" | "review" | "elevated" | "high";
  bandLabel: string;
  signals: LinkSignal[];
};

const SHORTENERS = new Set([
  "bit.ly",
  "tinyurl.com",
  "t.co",
  "is.gd",
  "ow.ly",
  "rebrand.ly",
  "buff.ly",
  "cutt.ly",
]);

const REDIRECT_PARAMETERS = new Set(["url", "uri", "redirect", "redirect_url", "next", "continue", "dest", "destination", "target"]);
const DOWNLOAD_PATTERN = /\.(?:exe|scr|js|jse|vbs|vbe|bat|cmd|msi|iso|dmg)(?:$|[?#])/i;
const IP_HOST_PATTERN = /^(?:\d{1,3}\.){3}\d{1,3}$/;

function normalizedInput(input: string) {
  const trimmed = input.trim();
  return /^[a-zA-Z][a-zA-Z\d+.-]*:/.test(trimmed) ? trimmed : `https://${trimmed}`;
}

function bandFor(score: number): Pick<LinkAssessment, "band" | "bandLabel"> {
  if (score >= 55) return { band: "high", bandLabel: "إشارات عالية — لا تفتح الرابط" };
  if (score >= 30) return { band: "elevated", bandLabel: "إشارات مرتفعة — راجع الوجهة يدوياً" };
  if (score >= 12) return { band: "review", bandLabel: "إشارات تحتاج مراجعة" };
  return { band: "low", bandLabel: "لا تظهر إشارات محلية قوية" };
}

export function assessUrl(input: string): LinkAssessment {
  const candidate = normalizedInput(input);
  let parsed: URL;

  try {
    parsed = new URL(candidate);
  } catch {
    throw new Error("اكتب رابطاً صحيحاً، مثل https://example.com أو example.com.");
  }

  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    throw new Error("يدعم الفاحص روابط HTTP وHTTPS فقط. لم يتم فتح الرابط أو تنفيذه.");
  }

  const host = parsed.hostname.toLowerCase();
  const signals: LinkSignal[] = [];
  const push = (id: string, title: string, detail: string, points: number) => signals.push({ id, title, detail, points });

  if (parsed.protocol === "http:") {
    push("no-https", "لا يستخدم HTTPS", "الاتصال غير مشفّر؛ تجنّب إدخال أي بيانات حساسة.", 14);
  }
  if (parsed.username || parsed.password) {
    push("userinfo", "إخفاء وجهة داخل الرابط", "وجود @ أو بيانات مستخدم قد يخفي النطاق الفعلي الذي سيُفتح.", 25);
  }
  if (IP_HOST_PATTERN.test(host)) {
    push("ip-host", "العنوان يستخدم IP بدلاً من نطاق", "قد يكون مشروعاً في بعض الحالات، لكنه يستحق التحقق المستقل قبل المتابعة.", 20);
  }
  if (host.includes("xn--") || /[^\x00-\x7F]/.test(input)) {
    push("international-domain", "نطاق دولي أو مرمّز", "تحقق من اسم النطاق حرفياً؛ المحارف المتشابهة بصرياً قد تسبب التباساً.", 17);
  }
  if (SHORTENERS.has(host) || Array.from(SHORTENERS).some((shortener) => host.endsWith(`.${shortener}`))) {
    push("shortener", "رابط مختصر", "الوجهة النهائية غير ظاهرة في النص؛ لا تفتحه قبل التحقق من مصدره.", 13);
  }
  if (host.length > 45 || host.split(".").length >= 5) {
    push("complex-host", "نطاق طويل أو متعدد المستويات", "افحص الجزء الأخير من النطاق؛ اسم العلامة في بداية العنوان لا يثبت الملكية.", 7);
  }
  if (parsed.port && parsed.port !== "80" && parsed.port !== "443") {
    push("custom-port", "منفذ غير معتاد", "استخدام منفذ مخصص ليس دليلاً على الخطر، لكنه يحتاج إلى سياق موثوق.", 7);
  }
  if (DOWNLOAD_PATTERN.test(parsed.pathname)) {
    push("download", "ملف قابل للتنفيذ أو التثبيت", "لا تشغّل الملف قبل فحص مصدره والتأكد من سلامته.", 18);
  }
  if (parsed.search.includes("%")) {
    push("encoded-query", "معلمات مشفّرة", "قد تخفي المعلمات وجهة أو محتوى إضافياً؛ راجع الرابط قبل إدخال بيانات.", 5);
  }
  if (Array.from(parsed.searchParams.keys()).some((key) => REDIRECT_PARAMETERS.has(key.toLowerCase()))) {
    push("redirect", "معلمة إعادة توجيه", "قد يحوّل الرابط إلى موقع آخر؛ تحقق من الوجهة النهائية عبر قناة مستقلة.", 8);
  }

  const score = Math.min(100, signals.reduce((total, signal) => total + signal.points, 0));
  return {
    normalized: parsed.toString(),
    host,
    protocol: parsed.protocol.replace(":", "").toUpperCase(),
    score,
    ...bandFor(score),
    signals,
  };
}
