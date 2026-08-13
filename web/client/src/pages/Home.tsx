/**
 * Phoenix Command Center — cinematic, calm, defensive command interface.
 * Phone-number structure inspection remains the primary tool; safety tools are supporting stations.
 */
import { assessMessage, type LensAssessment } from "@/lib/message-security";
import { assessUrl, type LinkAssessment } from "@/lib/url-security";
import "@/command-actions.css";
import "@/command-refinement.css";
import { EvidenceCapsule, type CapsuleSource } from "@/components/EvidenceCapsule";
import jsQR from "jsqr";
import {
  Activity,
  ArrowUpRight,
  Check,
  CheckCircle2,
  ChevronLeft,
  CircleAlert,
  ClipboardCheck,
  Copy,
  FileText,
  ImageUp,
  Link2,
  LockKeyhole,
  MessageSquareWarning,
  Network,
  Phone,
  QrCode,
  Radar,
  ScanLine,
  ShieldCheck,
  Sparkles,
  Upload,
} from "lucide-react";
import { FormEvent, useMemo, useState } from "react";
import { parsePhoneNumberFromString } from "libphonenumber-js";

type StationId = "number" | "link" | "message" | "qr" | "capsule";

type NumberResult = {
  e164: string;
  international: string;
  country: string;
  callingCode: string;
  type: string;
};

type AnalysisResult =
  | { kind: "number"; score: number; title: string; subtitle: string; points: string[]; response: string[] }
  | { kind: "link"; score: number; title: string; subtitle: string; points: string[]; response: string[] }
  | { kind: "message"; score: number; title: string; subtitle: string; points: string[]; response: string[] }
  | { kind: "qr"; score: number; title: string; subtitle: string; points: string[]; response: string[] };

const commandHero = `${import.meta.env.BASE_URL}assets/phoenix-command-hero.webp`;
const phoenixMark = `${import.meta.env.BASE_URL}assets/phoenix-official-mark.webp`;

const stations: Array<{ id: StationId; label: string; sublabel: string; icon: typeof Phone }> = [
  { id: "number", label: "بنية الرقم", sublabel: "المحطة الأساسية", icon: Phone },
  { id: "link", label: "سلامة الرابط", sublabel: "فحص محلي", icon: Link2 },
  { id: "message", label: "Phoenix Lens", sublabel: "نص الرسائل", icon: MessageSquareWarning },
  { id: "qr", label: "مختبر QR", sublabel: "صورة محلية", icon: QrCode },
  { id: "capsule", label: "كبسولة الأدلة", sublabel: "قضية محلية", icon: ClipboardCheck },
];

function phoneType(type: string | undefined) {
  const labels: Record<string, string> = {
    MOBILE: "هاتف محمول",
    FIXED_LINE: "خط ثابت",
    FIXED_LINE_OR_MOBILE: "ثابت أو محمول",
    VOIP: "رقم VoIP",
    TOLL_FREE: "رقم مجاني",
    PREMIUM_RATE: "رقم مدفوع",
  };
  return labels[type ?? ""] ?? "غير محدد";
}

function band(score: number) {
  if (score >= 55) return { label: "مراجعة عاجلة", tone: "danger" };
  if (score >= 30) return { label: "مراجعة مرتفعة", tone: "warning" };
  if (score >= 12) return { label: "تحقق إضافي", tone: "caution" };
  return { label: "إشارات مستقرة", tone: "safe" };
}

function ScoreDial({ score, verified = false }: { score: number; verified?: boolean }) {
  const visualScore = verified ? 100 : score;
  return (
    <div className={`score-dial ${verified ? "score-dial--verified" : ""}`} style={{ "--score": `${visualScore}%` } as React.CSSProperties}>
      <strong>{visualScore}</strong>
      <span>{verified ? "تحقق" : "/ 100"}</span>
    </div>
  );
}

function EmptyReadout() {
  return (
    <div className="empty-readout">
      <div className="scan-orb"><ScanLine size={27} /></div>
      <h3>بانتظار الإشارة.</h3>
      <p>اختر محطة من اليسار، ثم استخدم المثال الجاهز أو أدخل بياناتك لتظهر القراءة هنا.</p>
      <div className="empty-readout__grid" aria-hidden="true" />
    </div>
  );
}

export default function Home() {
  const [station, setStation] = useState<StationId>(() => {
    const candidate = new URLSearchParams(window.location.search).get("tool") as StationId | null;
    return candidate && stations.some((item) => item.id === candidate) ? candidate : "number";
  });
  const [showGuide, setShowGuide] = useState(true);
  const [numberInput, setNumberInput] = useState("");
  const [linkInput, setLinkInput] = useState("");
  const [messageInput, setMessageInput] = useState("");
  const [qrStatus, setQrStatus] = useState("اختر صورة QR من جهازك. لن تُرفع الصورة.");
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [notice, setNotice] = useState("");
  const [activity, setActivity] = useState("المركز جاهز. ابدأ من محطة بنية الرقم.");
  const [copied, setCopied] = useState(false);

  const currentStation = useMemo(() => stations.find((item) => item.id === station) ?? stations[0], [station]);

  function chooseStation(next: StationId) {
    setStation(next);
    window.history.replaceState({}, "", `${window.location.pathname}?tool=${next}`);
    setNotice("");
    setCopied(false);
    setActivity(`تم تجهيز محطة ${stations.find((item) => item.id === next)?.label ?? "التحليل"}.`);
  }

  function readNumber(raw: string) {
    setNotice("");
    const phone = parsePhoneNumberFromString(raw.trim());
    if (!phone || !phone.isPossible() || !phone.isValid()) {
      setResult(null);
      setNotice("أدخل رقماً دولياً صحيحاً يبدأ بـ +، مثل +12025550123.");
      return;
    }
    const details: NumberResult = {
      e164: phone.number,
      international: phone.formatInternational(),
      country: phone.country ?? "غير محدد",
      callingCode: `+${phone.countryCallingCode}`,
      type: phoneType(phone.getType()),
    };
    setResult({
      kind: "number",
      score: 100,
      title: "بنية الرقم متماسكة",
      subtitle: `${details.country} · ${details.type} · ${details.callingCode}`,
      points: [`الصيغة المعيارية: ${details.e164}`, `الصيغة الدولية: ${details.international}`, `الدولة/المنطقة: ${details.country}`, `تصنيف الرقم: ${details.type}`],
      response: ["هذه قراءة لخطة الترقيم العامة، لا لهوية المالك.", "لا تستخدم النتيجة لتحديد موقع جهاز أو شخص.", "انسخ التقرير عند الحاجة إلى توثيق داخلي."],
    });
    setActivity(`تمت قراءة بنية ${details.e164} بنجاح.`);
  }

  function analyzeNumber(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    readNumber(numberInput);
  }

  function readLink(raw: string) {
    setNotice("");
    try {
      const assessment: LinkAssessment = assessUrl(raw);
      setResult({
        kind: "link",
        score: assessment.score,
        title: assessment.bandLabel,
        subtitle: `${assessment.host} · ${assessment.protocol} · لم يتم فتح الرابط`,
        points: assessment.signals.length ? assessment.signals.map((signal) => signal.title) : ["لا تظهر إشارات محلية قوية في بنية الرابط."],
        response: assessment.score >= 30 ? ["لا تفتح الرابط من الرسالة.", "تحقق من الجهة عبر موقعها المعروف.", "لا تدخل كلمة مرور أو رمز MFA."] : ["النتيجة ليست ضماناً للأمان.", "تحقق من مصدر الرسالة وسياقها.", "لا تدخل معلومات حساسة بلا تحقق مستقل."],
      });
      setActivity(`فُحص الرابط محلياً: ${assessment.host}.`);
    } catch (error) {
      setResult(null);
      setNotice(error instanceof Error ? error.message : "تعذر فحص الرابط.");
    }
  }

  function analyzeLink(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    readLink(linkInput);
  }

  function readMessage(raw: string) {
    setNotice("");
    try {
      const assessment: LensAssessment = assessMessage(raw);
      setResult({
        kind: "message",
        score: assessment.score,
        title: assessment.label,
        subtitle: `${assessment.signals.length} إشارة محلية · ${assessment.urls.length ? "تم فحص الرابط دون فتحه" : "لا يوجد رابط"}`,
        points: assessment.signals.length ? assessment.signals.map((signal) => signal.title) : ["لا تظهر إشارات محلية قوية في النص."],
        response: assessment.steps,
      });
      setActivity("حللت Phoenix Lens النص محلياً من دون إرساله إلى أي خدمة.");
    } catch (error) {
      setResult(null);
      setNotice(error instanceof Error ? error.message : "تعذر تحليل النص.");
    }
  }

  function analyzeMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    readMessage(messageInput);
  }

  function runQuickDemo() {
    const example = "+12025550123";
    chooseStation("number");
    setNumberInput(example);
    readNumber(example);
    document.getElementById("workspace")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function decodeQr(file: File) {
    setNotice("");
    setQrStatus("جاري قراءة الرمز داخل متصفحك…");
    const objectUrl = URL.createObjectURL(file);
    const image = new Image();
    image.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = image.naturalWidth;
      canvas.height = image.naturalHeight;
      const context = canvas.getContext("2d", { willReadFrequently: true });
      if (!context) {
        setQrStatus("تعذر إنشاء مساحة قراءة للصورة.");
        URL.revokeObjectURL(objectUrl);
        return;
      }
      context.drawImage(image, 0, 0);
      const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
      const code = jsQR(imageData.data, imageData.width, imageData.height, { inversionAttempts: "attemptBoth" });
      URL.revokeObjectURL(objectUrl);
      if (!code) {
        setQrStatus("لم يتم العثور على QR صالح. جرّب صورة أوضح ومربعة.");
        return;
      }
      const raw = code.data.trim();
      let score = 0;
      let points = [`المحتوى المقروء: ${raw.slice(0, 120)}${raw.length > 120 ? "…" : ""}`];
      let response = ["لم يُفتح المحتوى تلقائياً.", "راجع النص أو الرابط قبل أي تفاعل.", "احذف الصورة من جهازك إذا كانت حساسة."];
      try {
        const link = assessUrl(raw);
        score = link.score;
        points = link.signals.length ? link.signals.map((signal) => `QR → ${signal.title}`) : ["QR يحتوي رابطاً بلا إشارات محلية قوية."];
        response = score >= 30 ? ["لا تفتح الرابط من QR.", "اكتب عنوان الجهة يدوياً للتحقق.", "لا تقدم كلمة مرور أو رمزاً على صفحة غير مؤكدة."] : response;
      } catch {
        // A QR may legitimately contain non-URL text; it stays a local readout.
      }
      setQrStatus("تمت القراءة محلياً. لم يتم رفع الصورة أو فتح محتواها.");
      setResult({ kind: "qr", score, title: score ? band(score).label : "تمت قراءة رمز QR", subtitle: "مختبر QR محلي · لم يتم فتح المحتوى", points, response });
      setActivity("تمت قراءة QR محلياً وإرسال محتواه إلى محطة المراجعة فقط.");
    };
    image.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      setQrStatus("تعذر تحميل الصورة. اختر ملف PNG أو JPG صالحاً.");
    };
    image.src = objectUrl;
  }

  async function copyReport() {
    if (!result) return;
    const report = [
      "Phoenix — تقرير مركز القيادة",
      `الحالة: ${result.title}`,
      `الدرجة: ${result.kind === "number" ? "تحقق بنيوي" : `${result.score}/100`}`,
      `الملخص: ${result.subtitle}`,
      "الإشارات:",
      ...result.points.map((point) => `- ${point}`),
      "خطة التصرف:",
      ...result.response.map((step, index) => `${index + 1}. ${step}`),
      "تم التحليل محلياً داخل المتصفح.",
    ].join("\n");
    await navigator.clipboard.writeText(report);
    setCopied(true);
  }

  const safetyBand = result ? (result.kind === "number" ? { label: "بنية مؤكدة", tone: "safe" } : band(result.score)) : { label: "وضع استعداد", tone: "neutral" };
  const capsuleSource: CapsuleSource | null = result ? { ...result } : null;

  return (
    <div className="command-app" dir="rtl">
      <aside className="command-rail">
        <div className="brand-system">
          <img className="brand-system__mark" src={phoenixMark} alt="رمز Phoenix" />
          <div><strong>Phoenix</strong><span>LOCAL VERIFICATION</span></div>
        </div>
        <div className="rail-rule" />
        <nav className="station-nav" aria-label="محطات Phoenix">
          {stations.map(({ id, label, sublabel, icon: Icon }, index) => (
            <button key={id} onClick={() => chooseStation(id)} className={`station-nav__item ${station === id ? "is-active" : ""}`}>
              <span className="station-nav__index">0{index + 1}</span><Icon size={18} /><span><strong>{label}</strong><small>{sublabel}</small></span>
            </button>
          ))}
        </nav>
        <div className="rail-bottom">
          <div><span>المعالجة</span><strong><i /> تعمل محلياً</strong></div>
          <div><span>الإصدار</span><strong>2026.2 / LOCAL</strong></div>
        </div>
      </aside>

      <main className="command-main">
        <section className={`command-hero ${station === "number" ? "" : "command-hero--workbench"}`} style={{ backgroundImage: `linear-gradient(90deg, rgba(5,9,10,.94) 0%, rgba(5,9,10,.76) 38%, rgba(5,9,10,.20) 100%), url(${commandHero})` }}>
          <header className="command-topbar">
            <div className="system-status"><span className="live-dot" /> نظام التقييم المحلي متصل</div>
            <div className="topbar-actions"><button onClick={() => setShowGuide((value) => !value)}><FileText size={15} /> {showGuide ? "إخفاء الدليل" : "دليل التجربة"}</button><span className="timestamp"><ClockLabel /></span></div>
          </header>
          <div className="hero-copy">
            <p className="command-kicker"><Sparkles size={15} /> مركز قراءة الإشارات</p>
            <h1>افحص <em>قبل</em> أن تثق.</h1>
            <p>أداة تحقق محلية لقراءة بنية الأرقام والإشارات المرتبطة بها. لا تتبع، لا رفع، ولا حكم على الأشخاص.</p>
            <div className="hero-actions"><button onClick={runQuickDemo}><ScanLine size={17} /> شغّل تجربة فورية</button><button onClick={() => setShowGuide(true)}>كيف أستخدم الأدوات؟ <ChevronLeft size={16} /></button></div>
            <div className="hero-metrics"><span><strong>04</strong> محطات دفاعية</span><span><strong>0</strong> بيانات مرفوعة</span><span><strong>100%</strong> تحليل محلي</span></div>
          </div>
          <div className="hero-glass-card"><Radar size={25} /><span>ملاحظة تحقق</span><strong>التحقق المستقل<br />أقوى من الاستعجال.</strong><small>PHX / REVIEW 01</small></div>
        </section>

        {showGuide && <section className="try-guide"><div className="try-guide__head"><ClipboardCheck size={20} /><div><p>كيف تجرّبها خلال دقيقة؟</p><span>ابدأ بمثال جاهز، ثم جرّب بياناتك أنت فقط.</span></div><button onClick={() => setShowGuide(false)}>×</button></div><div className="try-guide__steps"><span><b>1</b> اختر محطة</span><span><b>2</b> استخدم المثال</span><span><b>3</b> اقرأ الإشارات</span><span><b>4</b> انسخ التقرير</span></div></section>}

        <section className="command-workspace" id="workspace">
          <div className="workspace-head"><div><p className="command-kicker">المحطة النشطة / {currentStation.label}</p><h2>{station === "number" ? "فحص بنية رقم دولي" : station === "link" ? "اقرأ الرابط قبل فتحه" : station === "message" ? "ضع الرسالة تحت العدسة" : station === "qr" ? "فك محتوى QR بأمان" : "اجمع الأدلة قبل أن يختفي السياق"}</h2><div className="measurement-strip" aria-hidden="true"><span /><span /><span /><span /><span /><span /><span /><span /></div></div><div className={`safety-chip safety-chip--${station === "capsule" ? "neutral" : safetyBand.tone}`}><ShieldCheck size={16} /> {station === "capsule" ? "جلسة محلية" : safetyBand.label}</div></div>
          <div className={`workspace-grid ${station === "capsule" ? "workspace-grid--capsule" : ""}`}>
            {station === "capsule" ? <EvidenceCapsule source={capsuleSource} onActivity={setActivity} /> : <><section className="tool-console">
              {station === "number" && <form onSubmit={analyzeNumber}><ToolLabel icon={Phone} label="رقم دولي" hint="مثال: +12025550123" /><div className="command-input"><span>+ / E.164</span><input value={numberInput} onChange={(event) => setNumberInput(event.target.value)} placeholder="+12025550123" dir="ltr" /></div><div className="tool-actions"><button className="primary-action" type="submit"><ScanLine size={17} /> تحليل الرقم</button><button type="button" className="ghost-action" onClick={() => { const value = "+12025550123"; setNumberInput(value); readNumber(value); }}>تشغيل مثال</button></div></form>}
              {station === "link" && <form onSubmit={analyzeLink}><ToolLabel icon={Link2} label="رابط للفحص" hint="لن نفتح الرابط" /><div className="command-input"><span>URL</span><input value={linkInput} onChange={(event) => setLinkInput(event.target.value)} placeholder="https://example.com/login" dir="ltr" /></div><div className="tool-actions"><button className="primary-action" type="submit"><ShieldCheck size={17} /> فحص الرابط</button><button type="button" className="ghost-action" onClick={() => { const value = "http://notice@127.0.0.1:8080/update.exe?redirect=https%3A%2F%2Fexample.com"; setLinkInput(value); readLink(value); }}>تشغيل مثال</button></div></form>}
              {station === "message" && <form onSubmit={analyzeMessage}><ToolLabel icon={MessageSquareWarning} label="رسالة أو محتوى بريد" hint="لا يخرج النص من المتصفح" /><textarea className="command-textarea" value={messageInput} onChange={(event) => setMessageInput(event.target.value)} placeholder="ألصق رسالة وصلت إليك هنا…" /><div className="tool-actions"><button className="primary-action" type="submit"><Radar size={17} /> تحليل تحت العدسة</button><button type="button" className="ghost-action" onClick={() => { const value = "عاجل: تم تعليق حسابك. افتح https://bit.ly/verify وأدخل كلمة المرور ورمز OTP الآن."; setMessageInput(value); readMessage(value); }}>تشغيل مثال</button></div></form>}
              {station === "qr" && <div><ToolLabel icon={QrCode} label="صورة QR" hint="PNG أو JPG · قراءة محلية" /><label className="qr-dropzone"><ImageUp size={29} /><strong>اسحب صورة أو اخترها من جهازك</strong><span>{qrStatus}</span><input type="file" accept="image/png,image/jpeg,image/webp" onChange={(event) => event.target.files?.[0] && decodeQr(event.target.files[0])} /></label><div className="tool-actions"><button type="button" className="ghost-action" onClick={() => setQrStatus("أنشئ أو صوّر QR يحتوي رابطاً، ثم ارفعه هنا. لن يتم فتحه تلقائياً.")}>كيف أجرب QR؟</button></div></div>}
              {notice && <div className="command-notice"><CircleAlert size={18} /> {notice}</div>}
              <div className="privacy-line"><LockKeyhole size={14} /> لا تُخزَّن إدخالاتك ولا تُرسل إلى خادم خارجي.</div>
            </section>
            <section className="readout-panel">
              <div className="readout-top"><span>READOUT / PHX-{station.toUpperCase()}</span><Activity size={16} /></div>
              {result ? <div className="result-readout"><div className="result-summary"><ScoreDial score={result.score} verified={result.kind === "number"} /><div><p>{result.title}</p><span>{result.subtitle}</span></div><button onClick={copyReport} className="copy-report">{copied ? <Check size={15} /> : <Copy size={15} />}{copied ? "نُسخ" : "نسخ"}</button></div><div className="signal-table"><p>إشارات القراءة</p>{result.points.map((point, index) => <div key={`${point}-${index}`}><span>{String(index + 1).padStart(2, "0")}</span><strong>{point}</strong></div>)}</div><div className="protocol-list"><p><ShieldCheck size={15} /> بروتوكول التصرف</p>{result.response.map((step, index) => <div key={step}><b>{index + 1}</b><span>{step}</span></div>)}</div></div> : <EmptyReadout />}
            </section></>}
          </div>
        </section>

        <section className="command-footer-grid"><div className="command-log"><span className="command-log__label"><Network size={15} /> سجل المركز</span><strong>{activity}</strong></div><div className="command-ethics"><span>حدود Phoenix</span><p>تفحص البنية والإشارات فقط. لا تكشف اسم صاحب رقم أو موقع هاتف أو حسابات شخصية.</p></div><button className="scroll-top" onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}><ArrowUpRight size={18} /> أعلى المركز</button></section>
      </main>
    </div>
  );
}

function ToolLabel({ icon: Icon, label, hint }: { icon: typeof Phone; label: string; hint: string }) {
  return <div className="tool-label"><span><Icon size={17} /> {label}</span><small>{hint}</small></div>;
}

function ClockLabel() {
  const [time] = useState(() => new Intl.DateTimeFormat("ar", { hour: "2-digit", minute: "2-digit", hour12: true }).format(new Date()));
  return <>{time} / LOCAL</>;
}
