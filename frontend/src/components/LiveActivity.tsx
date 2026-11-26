import { useEffect, useRef, useState } from "react";
import {
  Activity,
  Clock3,
  Database,
  Radio,
  RefreshCw,
  Timer,
} from "lucide-react";
import { request } from "../api";
import type { ActivityResponse } from "../types";
import { formatDate, number } from "../labels";

const sourceNames: Record<string, string> = {
  finder: "مبادرة منح غزة",
  iefa: "IEFA",
  scholarpal: "ScholarPal",
  official: "جهة رسمية",
  scholars4dev: "Scholars4dev",
  amideast: "Amideast",
};
export function LiveActivity({ onOpen }: { onOpen: (id: string) => void }) {
  const [data, setData] = useState<ActivityResponse>();
  const [error, setError] = useState("");
  const [fresh, setFresh] = useState<Set<string>>(new Set());
  const known = useRef<Set<string> | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    const load = () =>
      request<ActivityResponse>("/stream/activity?limit=40", {
        signal: controller.signal,
      })
        .then((next) => {
          if (controller.signal.aborted) return;
          setFresh(
            new Set(
              known.current
                ? next.events
                    .filter((event) => !known.current!.has(event.event_id))
                    .map((event) => event.event_id)
                : [],
            ),
          );
          known.current = new Set(next.events.map((event) => event.event_id));
          setData(next);
          setError("");
        })
        .catch((reason) => {
          if (!controller.signal.aborted) setError(reason.message);
        });
    void load();
    const interval = setInterval(load, 3000);
    return () => {
      controller.abort();
      clearInterval(interval);
    };
  }, []);
  const schedule = data?.schedule;
  const collectorConnected = schedule?.scheduler_connected === true;
  return (
    <main className="secondary-page live-page">
      <div className="page-heading">
        <h1>البث المباشر للمنح</h1>
        <p>
          شاهد وصول الإعلانات والتحديثات الفعلية من المصادر إلى النظام، بوقت
          الرصد والحفظ.
        </p>
      </div>
      {error && (
        <p className="error-copy" role="alert">
          {error}
        </p>
      )}
      <div className="pipeline-flow" aria-label="مسار معالجة البيانات">
        <div>
          <Radio />
          <strong>المصادر</strong>
          <span>جمع دوري</span>
        </div>
        <div>
          <Activity />
          <strong>Kafka</strong>
          <span>أحداث جديدة وتحديثات</span>
        </div>
        <div>
          <RefreshCw />
          <strong>Spark</strong>
          <span>معالجة متدفقة</span>
        </div>
        <div>
          <Database />
          <strong>MongoDB</strong>
          <span>حفظ وإتاحة للموقع</span>
        </div>
      </div>
      <section className="live-metrics">
        <div>
          <span>اتصال المعالج</span>
          <strong
            className={
              data?.streaming?.processor_connected ? "processor-online" : ""
            }
          >
            {data?.streaming?.processor_connected
              ? "متصل وينتظر الأحداث"
              : "لا توجد إشارة حديثة"}
          </strong>
          <small>
            آخر إشارة:{" "}
            {formatDate(
              data?.streaming?.runtime?.last_heartbeat_at,
              true,
              true,
            )}
          </small>
        </div>
        <div>
          <span>أحداث البث المحفوظة</span>
          <strong data-testid="stream-event-count">
            {number(data?.streaming?.processed_events || 0)}
          </strong>
          <small>تتضمن إضافة الإعلانات وتحديثها</small>
        </div>
        <div>
          <span>الجمع التالي المتوقع</span>
          <strong>
            {collectorConnected && schedule?.next_run_at
              ? formatDate(schedule.next_run_at, true)
              : "الجمع الدوري غير متصل حاليًا"}
          </strong>
          <small>
            كل {number((schedule?.interval_seconds || 21600) / 3600)} ساعات عند
            تشغيل جهازك والخدمات
          </small>
        </div>
      </section>
      <div className="live-status-line">
        <span>
          <Timer size={16} />
          {!collectorConnected
            ? "الجمع الدوري متوقف أو لا توجد إشارة حديثة"
            : schedule?.status === "running"
              ? "يجري جمع المصادر الآن"
              : "بين دورات الجمع؛ يستقبل Spark أي أحداث تصل إلى Kafka"}
        </span>
        <span>آخر بدء جمع: {formatDate(schedule?.run_started_at, true)}</span>
      </div>
      <section className="event-feed" aria-label="سجل أحداث البث">
        <div className="event-feed-heading">
          <h2>آخر الأحداث المحفوظة</h2>
          <span>
            <RefreshCw size={15} />
            يتحدث كل 3 ثوانٍ
          </span>
        </div>
        {!data ? (
          <p className="loading-state">جارٍ قراءة سجل المعالجة…</p>
        ) : !data.events.length ? (
          <p className="empty-state">لا توجد أحداث بث مسجلة بعد.</p>
        ) : (
          data.events.map((event) => (
            <article
              key={event.event_id}
              className={
                "stream-event " +
                (fresh.has(event.event_id) ? "event-arrived" : "")
              }
              data-event-id={event.event_id}
            >
              <span className={"event-kind " + event.event_type}>
                {event.event_type === "discovered"
                  ? "إضافة"
                  : event.event_type === "updated"
                    ? "تحديث"
                    : "إغلاق"}
              </span>
              <div className="event-body">
                <button
                  onClick={() => onOpen(event.scholarship_id)}
                  className="event-title"
                  dir="auto"
                >
                  {event.title}
                </button>
                <p>
                  {sourceNames[event.source_id] || event.source_id} ·{" "}
                  {event.mode === "replay" ? "إعادة بث تجريبية" : "بث حقيقي"}
                  {event.applied === false
                    ? " · استُقبل دون استبدال نسخة أحدث"
                    : " · تم الحفظ"}
                </p>
                <div className="event-times">
                  <span>
                    <Clock3 size={14} />
                    رُصد: {formatDate(event.observed_at, true, true)}
                  </span>
                  <span>
                    حُفظ:{" "}
                    <time dateTime={event.processed_at}>
                      {formatDate(event.processed_at, true, true)}
                    </time>
                  </span>
                </div>
                {event.transport && (
                  <code dir="ltr" className="event-transport">
                    {event.transport.topic} · partition{" "}
                    {event.transport.partition} · offset{" "}
                    {event.transport.offset}
                  </code>
                )}
              </div>
            </article>
          ))
        )}
      </section>
      <p className="form-hint">
        وقت الإضافة في بطاقة المنحة يبقى ثابتًا؛ وقت التحديث يتغيّر عند حفظ نسخة
        أحدث. تُعرض بيانات إعادة البث بوسمها عند استخدامها.
      </p>
    </main>
  );
}
