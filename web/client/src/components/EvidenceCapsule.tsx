/** Phoenix Evidence Capsule: an in-browser integrity and decision record. */
import { downloadJson, fingerprintFile, type FileEvidence } from "@/lib/evidence";
import { Archive, CheckCircle2, Download, FilePlus2, FileText, Fingerprint, LockKeyhole, Plus, ShieldAlert, Trash2 } from "lucide-react";
import { ChangeEvent, useMemo, useState } from "react";
import "@/evidence-capsule.css";

export type CapsuleSource = {
  kind: string;
  score: number;
  title: string;
  subtitle: string;
  points: string[];
  response: string[];
};

type CapsuleEvent = {
  id: string;
  at: string;
  label: string;
  detail: string;
  category: "source" | "file" | "note";
};

function formatTime(value: string) {
  return new Intl.DateTimeFormat("ar", { hour: "2-digit", minute: "2-digit", second: "2-digit" }).format(new Date(value));
}

function formatSize(bytes: number) {
  return bytes < 1024 * 1024 ? `${Math.ceil(bytes / 1024)} KB` : `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function EvidenceCapsule({ source, onActivity }: { source: CapsuleSource | null; onActivity: (value: string) => void }) {
  const [caseTitle, setCaseTitle] = useState("قضية Phoenix محلية");
  const [note, setNote] = useState("");
  const [files, setFiles] = useState<FileEvidence[]>([]);
  const [events, setEvents] = useState<CapsuleEvent[]>([]);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");

  const boundaries = useMemo(() => {
    const corpus = `${source?.title ?? ""} ${source?.subtitle ?? ""} ${source?.points.join(" ") ?? ""} ${note}`.toLowerCase();
    return [
      { label: "الهوية", active: source?.kind === "number" || /هوية|رقم|identity/.test(corpus), hint: "ادعاء معرفة شخص أو صفة جهة" },
      { label: "الدخول", active: /كلمة المرور|رمز|otp|mfa|password|access/.test(corpus), hint: "كلمة مرور أو رمز أو جلسة" },
      { label: "المال", active: /دفع|تحويل|بطاق|فاتورة|payment|bank|card/.test(corpus), hint: "تحويل أو بطاقة أو مطالبة مالية" },
      { label: "الجهاز", active: /تنزيل|ملف|qr|رابط|download|file/.test(corpus), hint: "رابط أو تنزيل أو محتوى QR" },
    ];
  }, [note, source]);

  function addEvent(event: Omit<CapsuleEvent, "id" | "at">) {
    setEvents((current) => [{ id: crypto.randomUUID(), at: new Date().toISOString(), ...event }, ...current]);
  }

  function captureSource() {
    if (!source) {
      setNotice("شغّل أي محطة أولاً، ثم ارجع هنا لإضافة قراءتها إلى الكبسولة.");
      return;
    }
    addEvent({ category: "source", label: source.title, detail: source.subtitle });
    setNotice("أضيفت قراءة المحطة إلى خط القضية المحلي.");
    onActivity("أُضيفت نتيجة المحطة الحالية إلى كبسولة الأدلة المحلية.");
  }

  function saveNote() {
    if (!note.trim()) {
      setNotice("اكتب ملاحظة موجزة أولاً.");
      return;
    }
    addEvent({ category: "note", label: "ملاحظة المستخدم", detail: note.trim() });
    setNotice("حُفظت الملاحظة ضمن الجلسة المحلية.");
    setNote("");
  }

  async function addFiles(event: ChangeEvent<HTMLInputElement>) {
    const selected = Array.from(event.target.files ?? []);
    if (!selected.length) return;
    setBusy(true);
    setNotice("جاري حساب البصمة محلياً…");
    try {
      const fingerprints = await Promise.all(selected.map((file) => fingerprintFile(file)));
      setFiles((current) => [...fingerprints, ...current]);
      fingerprints.forEach((file) => addEvent({ category: "file", label: `بصمة ملف: ${file.name}`, detail: `SHA-256 ${file.sha256.slice(0, 18)}…` }));
      setNotice(`تمت بصمة ${fingerprints.length} ملف محلياً؛ لم يُرفع أي ملف.`);
      onActivity(`تمت إضافة ${fingerprints.length} بصمة SHA-256 إلى الكبسولة.`);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "تعذر حساب بصمة الملف.");
    } finally {
      setBusy(false);
      event.target.value = "";
    }
  }

  function exportCase() {
    const payload = {
      schema: "phoenix-evidence-capsule/1.0",
      caseId: `PHX-${crypto.randomUUID().slice(0, 8).toUpperCase()}`,
      title: caseTitle || "قضية Phoenix محلية",
      createdAt: new Date().toISOString(),
      locality: "Generated locally in the browser. No files were uploaded by Phoenix.",
      latestReading: source,
      trustBoundaries: boundaries,
      timeline: events,
      fileFingerprints: files,
      disclaimer: "A SHA-256 fingerprint records file integrity at the moment it was selected. It does not prove file origin, sender identity, or legal admissibility.",
    };
    downloadJson(`phoenix-evidence-${new Date().toISOString().slice(0, 10)}.json`, payload);
    setNotice("تم تنزيل التقرير JSON محلياً.");
    onActivity("تم إنشاء تقرير كبسولة الأدلة بصيغة JSON محلية.");
  }

  return (
    <section className="evidence-capsule">
      <div className="capsule-hero">
        <div className="capsule-mark"><Archive size={28} /></div>
        <div><p>PHX / EVIDENCE CAPSULE</p><h3>اجمع الدليل قبل أن يختفي السياق.</h3><span>الجلسة محلية: لا رفع، لا مزامنة، لا ادعاء بأن مصدر الملف موثوق.</span></div>
        <button onClick={exportCase} className="capsule-export"><Download size={16} /> تنزيل التقرير</button>
      </div>

      <div className="capsule-grid">
        <div className="capsule-card capsule-card--case">
          <div className="capsule-label"><Fingerprint size={15} /> ملف القضية</div>
          <label>اسم القضية<input value={caseTitle} onChange={(event) => setCaseTitle(event.target.value)} /></label>
          <button onClick={captureSource} className="capsule-primary"><Plus size={16} /> إضافة قراءة المحطة الحالية</button>
          <p className="capsule-muted">{source ? `القراءة المتاحة: ${source.title}` : "لا توجد قراءة بعد. شغّل محطة رقم أو رابط أو رسالة أولاً."}</p>
        </div>

        <div className="capsule-card capsule-card--boundaries">
          <div className="capsule-label"><ShieldAlert size={15} /> خريطة حدود الثقة</div>
          <p className="capsule-muted">ما الذي يحاول المحتوى دفعك لتجاوزه؟</p>
          <div className="boundary-map">{boundaries.map((boundary) => <div key={boundary.label} className={boundary.active ? "is-active" : ""}><span>{boundary.label}</span><small>{boundary.active ? "إشارة مرصودة" : boundary.hint}</small></div>)}</div>
        </div>

        <div className="capsule-card capsule-card--files">
          <div className="capsule-label"><Fingerprint size={15} /> بصمات الملفات</div>
          <label className="capsule-upload"><FilePlus2 size={20} /><span>{busy ? "جارٍ حساب SHA-256…" : "اختر ملفات للدليل المحلي"}</span><small>حتى 25 MB لكل ملف</small><input type="file" multiple onChange={addFiles} disabled={busy} /></label>
          <div className="fingerprint-list">{files.length ? files.map((file) => <div key={file.id}><CheckCircle2 size={15} /><span><strong>{file.name}</strong><small>{formatSize(file.size)} · SHA-256 {file.sha256.slice(0, 13)}…</small></span><button onClick={() => setFiles((current) => current.filter((item) => item.id !== file.id))} aria-label={`إزالة ${file.name}`}><Trash2 size={14} /></button></div>) : <p>لا توجد ملفات مختارة بعد.</p>}</div>
        </div>

        <div className="capsule-card capsule-card--note">
          <div className="capsule-label"><FileText size={15} /> ملاحظة سياقية</div>
          <textarea value={note} onChange={(event) => setNote(event.target.value)} placeholder="مثال: وصلت الرسالة الساعة 10:32، وطُلب تحويل مبلغ خلال عشر دقائق…" />
          <button onClick={saveNote} className="capsule-text-button">حفظ في الخط الزمني</button>
        </div>
      </div>

      <div className="capsule-timeline"><div className="capsule-label"><LockKeyhole size={15} /> الخط الزمني المحلي <small>{events.length} حدث</small></div>{events.length ? <div className="timeline-list">{events.map((event) => <div key={event.id} className={`timeline-event timeline-event--${event.category}`}><time>{formatTime(event.at)}</time><span /><div><strong>{event.label}</strong><p>{event.detail}</p></div></div>)}</div> : <div className="timeline-empty">ابدأ بإضافة قراءة أو ملف أو ملاحظة. ستظهر الأدلة مرتبة بالتوقيت هنا.</div>}</div>
      {notice && <div className="capsule-notice"><CheckCircle2 size={16} /> {notice}</div>}
    </section>
  );
}
