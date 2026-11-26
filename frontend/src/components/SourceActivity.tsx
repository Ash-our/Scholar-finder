import { useEffect, useState } from "react";
import { Activity, ExternalLink } from "lucide-react";
import { request } from "../api";
import type { SourceResponse } from "../types";
import { formatDate, number } from "../labels";

export function SourceActivity() {
  const [data, setData] = useState<SourceResponse | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    const load = () =>
      request<SourceResponse>("/sources", { signal: controller.signal })
        .then((next) => {
          if (!controller.signal.aborted) {
            setData(next);
            setError("");
          }
        })
        .catch((reason) => {
          if (!controller.signal.aborted) setError(reason.message);
        });
    void load();
    const interval = setInterval(load, 10_000);
    return () => {
      controller.abort();
      clearInterval(interval);
    };
  }, []);
  return (
    <main className="secondary-page">
      <div className="page-heading">
        <h1>نشاط المصادر</h1>
        <p>تعرّف على مصادر الإعلانات وآخر عمليات الجمع والمعالجة المسجلة.</p>
      </div>
      {error && (
        <p className="error-copy" role="alert">
          {error}
        </p>
      )}
      {data?.streaming && (
        <section className="stream-summary">
          <Activity size={25} />
          <div>
            <h2>المعالجة المتدفقة</h2>
            <p>
              {number(data.streaming.processed_events)} حدثًا محفوظًا ·{" "}
              {number(data.streaming.invalid_events)} سجلًا غير صالح
            </p>
          </div>
          <span>
            {data.streaming.windows.length
              ? "نوافذ معالجة مسجلة"
              : "بانتظار أول نافذة معالجة"}
          </span>
        </section>
      )}
      <section className="collection-timing">
        <h2>متى يجمع التطبيق البيانات؟</h2>
        <p>
          يبدأ الجمع مع تشغيل خدمات المشروع، ثم يتكرر كل{" "}
          {number((data?.schedule?.interval_seconds || 21600) / 3600)} ساعات.
          يحتاج بقاء الجهاز والخدمات شغّالة.
        </p>
        <div>
          <span>
            آخر بدء جمع:{" "}
            <strong>{formatDate(data?.schedule?.run_started_at, true)}</strong>
          </span>
          <span>
            الجمع التالي المتوقع:{" "}
            <strong>
              {data?.schedule?.scheduler_connected
                ? formatDate(data?.schedule?.next_run_at, true)
                : "الجمع الدوري غير متصل حاليًا"}
            </strong>
          </span>
        </div>
      </section>
      <div className="source-table-wrap">
        <table className="source-table">
          <thead>
            <tr>
              <th>المصدر</th>
              <th>حالة الربط</th>
              <th>آخر جمع ناجح</th>
              <th>الإعلانات في آخر جمع</th>
            </tr>
          </thead>
          <tbody>
            {data?.sources.map((source) => (
              <tr key={source.id}>
                <td>
                  <a href={source.url} target="_blank" rel="noreferrer">
                    {source.name}
                    <ExternalLink size={14} />
                  </a>
                  {source.note && <small>{source.note}</small>}
                </td>
                <td>
                  <span
                    className={`source-state ${source.last_run?.status || "planned"}`}
                  >
                    {!source.adapter
                      ? "مرجع مخطط"
                      : !source.last_run
                        ? "لم يُشغّل بعد"
                        : source.last_run.status === "running"
                          ? "قيد الجمع (آخر حالة مسجلة)"
                          : source.last_run.status === "ok"
                            ? "تم الجمع"
                            : source.last_run.status === "partial"
                              ? "جمع جزئي"
                              : "تعذر الجمع"}
                  </span>
                  {source.last_run?.error && (
                    <small>{source.last_run.error}</small>
                  )}
                </td>
                <td>{formatDate(source.last_run?.last_success_at, true)}</td>
                <td>
                  {source.last_run?.records !== undefined
                    ? number(source.last_run.records)
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {data?.streaming && data.streaming.windows.length > 0 && (
        <section className="window-panel">
          <h2>الأحداث حسب نوافذ زمنية</h2>
          <p className="muted">
            أعداد رسائل المصدر في نافذة 5 دقائق مع Watermark مدته 10 دقائق؛ لا
            تمثل عدد منح فريدة.
          </p>
          <div className="window-rows">
            {data.streaming.windows.slice(0, 12).map((window, index) => (
              <div key={`${window.source_id}-${window.window_start}-${index}`}>
                <strong>{window.source_id}</strong>
                <span>{formatDate(window.window_start, true)}</span>
                <span>
                  {window.event_type === "discovered"
                    ? "اكتشاف"
                    : window.event_type === "updated"
                      ? "تحديث"
                      : "إغلاق"}
                </span>
                <b>{number(window.count)}</b>
              </div>
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
