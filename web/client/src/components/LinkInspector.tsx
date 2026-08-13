/**
 * Design: غرفة عمليات هادئة — treat cyber signals as measured annotations,
 * never as dramatic verdicts; preserve the paper ledger and petrol/amber cues.
 */
import { Button } from "@/components/ui/button";
import { assessUrl, type LinkAssessment } from "@/lib/url-security";
import { AlertTriangle, Check, Copy, EyeOff, Link2, LockKeyhole, ShieldCheck } from "lucide-react";
import { FormEvent, useState } from "react";

function guidanceFor(assessment: LinkAssessment) {
  if (assessment.band === "high") {
    return "لا تفتح الرابط من الرسالة. اكتب موقع الجهة يدوياً أو تواصل معها من وسيلة معروفة للتحقق.";
  }
  if (assessment.band === "elevated" || assessment.band === "review") {
    return "قبل المتابعة، تحقق من اسم النطاق عبر مصدر مستقل ولا تدخل كلمة مرور أو رمز MFA في صفحة غير مؤكدة.";
  }
  return "لا تظهر إشارات محلية قوية، لكن هذا ليس ضماناً للأمان. تحقق دائماً من مصدر الرسالة وسياقها.";
}

export function LinkInspector() {
  const [value, setValue] = useState("");
  const [assessment, setAssessment] = useState<LinkAssessment | null>(null);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  function inspect(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCopied(false);
    setError("");
    try {
      setAssessment(assessUrl(value));
    } catch (nextError) {
      setAssessment(null);
      setError(nextError instanceof Error ? nextError.message : "تعذر تحليل الرابط.");
    }
  }

  async function copyReport() {
    if (!assessment) return;
    const lines = [
      "Phoenix — تقرير فحص رابط محلي",
      `النطاق: ${assessment.host}`,
      `البروتوكول: ${assessment.protocol}`,
      `الدرجة: ${assessment.score}/100`,
      `النتيجة: ${assessment.bandLabel}`,
      assessment.signals.length ? "الإشارات:" : "لا توجد إشارات محلية قوية.",
      ...assessment.signals.map((signal) => `- ${signal.title}: ${signal.detail}`),
      `توصية: ${guidanceFor(assessment)}`,
      "ملاحظة: لم يتم فتح الرابط أو الاتصال به أثناء هذا التحليل.",
    ];
    await navigator.clipboard.writeText(lines.join("\n"));
    setCopied(true);
  }

  return (
    <section className="link-inspector" aria-labelledby="link-inspector-title">
      <div className="cyber-heading">
        <div>
          <p className="eyebrow">دفاع سيبراني محلي</p>
          <h2 id="link-inspector-title">افحص شكل الرابط قبل أن تفتحه.</h2>
        </div>
        <div className="local-badge"><EyeOff size={14} /> لا فتح، لا طلبات شبكة</div>
      </div>
      <p className="cyber-intro">يفحص هذا القسم بنية الرابط داخل متصفحك فقط بحثاً عن إشارات تحتاج مراجعة. لا يزوره ولا يدّعي أن النتيجة حكم قطعي.</p>

      <form onSubmit={inspect} className="link-form">
        <label htmlFor="url-input" className="sr-only">الرابط المراد فحصه</label>
        <div className={`url-field ${error ? "url-field--error" : ""}`}>
          <Link2 size={21} />
          <input id="url-input" value={value} onChange={(event) => setValue(event.target.value)} placeholder="https://example.com/login" dir="ltr" inputMode="url" autoComplete="url" />
        </div>
        <Button type="submit" className="inspect-button">فحص الرابط <ShieldCheck size={18} /></Button>
      </form>
      {error && <div className="form-error" role="alert"><AlertTriangle size={18} /> {error}</div>}

      {assessment && (
        <div className="link-report" aria-live="polite">
          <div className={`risk-banner risk-banner--${assessment.band}`}>
            <div className="risk-score"><strong>{assessment.score}</strong><span>/100</span></div>
            <div><p>{assessment.bandLabel}</p><span>درجة تفسيرية لإشارات الرابط فقط، وليست تصنيفاً لسمعة الموقع.</span></div>
            <button type="button" className="copy-button" onClick={copyReport}>{copied ? <Check size={16} /> : <Copy size={16} />}{copied ? "تم النسخ" : "نسخ التقرير"}</button>
          </div>
          <div className="link-facts"><span><LockKeyhole size={14} /> {assessment.protocol}</span><strong dir="ltr">{assessment.host}</strong><span>{assessment.signals.length} إشارة</span></div>
          {assessment.signals.length ? (
            <div className="signal-list">
              {assessment.signals.map((signal) => <div className="signal-note" key={signal.id}><AlertTriangle size={16} /><div><strong>{signal.title}</strong><span>{signal.detail}</span></div></div>)}
            </div>
          ) : (
            <div className="clean-signal"><Check size={18} /> لم تظهر إشارات محلية قوية في بنية الرابط. راجع المصدر وسياق الرسالة قبل المتابعة.</div>
          )}
          <div className="cyber-guidance"><ShieldCheck size={19} /><span><strong>توصية Phoenix:</strong> {guidanceFor(assessment)}</span></div>
        </div>
      )}
    </section>
  );
}
