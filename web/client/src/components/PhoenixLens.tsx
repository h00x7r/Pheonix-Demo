/**
 * Design: غرفة عمليات هادئة — Phoenix Lens presents security signals as a
 * calm evidence ledger, using petrol structure and amber warnings without alarmist language.
 */
import { Button } from "@/components/ui/button";
import { assessMessage, type LensAssessment } from "@/lib/message-security";
import { AlertTriangle, Check, CircleAlert, ClipboardCheck, Copy, EyeOff, FileWarning, Link2, MessageSquareWarning, Search, ShieldCheck } from "lucide-react";
import { FormEvent, useState } from "react";

function iconForSource(source: "message" | "link") {
  return source === "link" ? <Link2 size={16} /> : <MessageSquareWarning size={16} />;
}

export function PhoenixLens() {
  const [value, setValue] = useState("");
  const [assessment, setAssessment] = useState<LensAssessment | null>(null);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  function analyze(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCopied(false);
    setError("");
    try {
      setAssessment(assessMessage(value));
    } catch (nextError) {
      setAssessment(null);
      setError(nextError instanceof Error ? nextError.message : "تعذر تحليل النص.");
    }
  }

  function fillExample() {
    setValue("عاجل: تم تعليق حسابك. اضغط https://example.com/verify وأدخل رمز التحقق خلال 10 دقائق لتجنب الإيقاف.");
    setAssessment(null);
    setError("");
  }

  async function copyReport() {
    if (!assessment) return;
    const lines = [
      "Phoenix Lens — تقرير دفاعي محلي",
      `النتيجة: ${assessment.label}`,
      `الدرجة: ${assessment.score}/100`,
      `الإشارات: ${assessment.signals.length}`,
      ...assessment.signals.map((signal) => `- ${signal.title}: ${signal.detail}`),
      "خطة التصرف:",
      ...assessment.steps.map((step, index) => `${index + 1}. ${step}`),
      "ملاحظة: تم تحليل النص محلياً. لم يتم فتح روابط أو إرسال محتوى إلى خدمة خارجية.",
    ];
    await navigator.clipboard.writeText(lines.join("\n"));
    setCopied(true);
  }

  return (
    <section className="lens-panel" aria-labelledby="lens-title">
      <div className="lens-heading">
        <div>
          <p className="eyebrow">Phoenix Lens / عدسة الحماية</p>
          <h2 id="lens-title">ضع الرسالة تحت العدسة قبل أن تتصرف.</h2>
        </div>
        <div className="local-badge"><EyeOff size={14} /> تحليل محلي، بلا إرسال أو فتح</div>
      </div>
      <p className="lens-intro">ألصق رسالة SMS أو بريد أو رابطاً. سنعرض إشارات الضغط وطلبات البيانات والرابط إن وُجد، ثم نحولها إلى خطة تصرف قصيرة وهادئة.</p>

      <form className="lens-form" onSubmit={analyze}>
        <label htmlFor="lens-message" className="sr-only">نص الرسالة أو الرابط المراد تحليله</label>
        <textarea id="lens-message" value={value} onChange={(event) => setValue(event.target.value)} placeholder="ألصق هنا رسالة وصلتك أو رابطاً تريد فهم إشاراته…" rows={5} />
        <div className="lens-actions">
          <Button type="submit" className="lens-submit"><Search size={18} /> تحليل تحت العدسة</Button>
          <button type="button" className="text-action" onClick={fillExample}>عرض مثال توعوي</button>
          <span><EyeOff size={14} /> لا تحفظ هذه الجلسة نصك</span>
        </div>
      </form>
      {error && <div className="form-error" role="alert"><AlertTriangle size={18} /> {error}</div>}

      {assessment && (
        <div className="lens-result" aria-live="polite">
          <div className={`lens-verdict lens-verdict--${assessment.band}`}>
            <div className="lens-score"><strong>{assessment.score}</strong><span>/100</span></div>
            <div><p>{assessment.label}</p><span>درجة تفسيرية لإشارات النص والرابط، وليست حكماً قاطعاً على المرسل أو الموقع.</span></div>
            <button type="button" className="copy-button" onClick={copyReport}>{copied ? <Check size={16} /> : <Copy size={16} />}{copied ? "تم النسخ" : "نسخ التقرير"}</button>
          </div>

          <div className="lens-map">
            <div className="evidence-rail">
              <div className="evidence-rail-title"><FileWarning size={17} /><span>خريطة الإشارات</span><small>{assessment.signals.length}</small></div>
              {assessment.signals.length ? assessment.signals.map((signal, index) => (
                <div className="evidence-item" key={signal.id}>
                  <div className="evidence-index">{String(index + 1).padStart(2, "0")}</div>
                  <div className={`evidence-source evidence-source--${signal.source}`}>{iconForSource(signal.source)}</div>
                  <div><strong>{signal.title}</strong><span>{signal.detail}</span></div>
                </div>
              )) : <div className="clean-signal"><Check size={18} /> لم تظهر إشارات محلية قوية في النص. تحقق من السياق عند أي طلب غير متوقع.</div>}
            </div>

            <aside className="incident-room">
              <div className="incident-heading"><ClipboardCheck size={18} /><span>غرفة الحادث</span></div>
              <p>جلسة محلية مؤقتة</p>
              <div className="incident-stat"><span>مستوى المراجعة</span><strong>{assessment.band === "high" ? "عاجل" : assessment.band === "elevated" ? "مرتفع" : assessment.band === "review" ? "متوسط" : "منخفض"}</strong></div>
              <div className="incident-stat"><span>مصادر الإشارة</span><strong>{assessment.urls.length ? "نص + رابط" : "نص"}</strong></div>
              <div className="incident-stat"><span>حالة الرابط</span><strong>{assessment.urls.length ? "لم يُفتح" : "لا يوجد"}</strong></div>
            </aside>
          </div>

          <div className="response-plan">
            <div className="response-title"><ShieldCheck size={19} /><div><p className="eyebrow">خطة التصرف</p><h3>ثلاث خطوات قبل أي تفاعل</h3></div></div>
            <div className="response-steps">{assessment.steps.map((step, index) => <div key={step}><span>{index + 1}</span><p>{step}</p></div>)}</div>
          </div>
        </div>
      )}
    </section>
  );
}
