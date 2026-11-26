import { useEffect, useState } from "react";
import { BarChart3, CalendarDays, RefreshCw } from "lucide-react";
import { request } from "../api";
import type { Filters, InsightsData, Profile } from "../types";
import {
  countryName,
  degreeLabels,
  formatDate,
  fundingLabels,
  number,
} from "../labels";

export function Insights({
  onOpen,
  filters,
  profile,
}: {
  onOpen: (id: string) => void;
  filters: Filters;
  profile: Profile | null;
}) {
  const [data, setData] = useState<InsightsData | null>(null);
  const [error, setError] = useState("");
  const [loaded, setLoaded] = useState(false);
  const key = JSON.stringify({ filters, profile });
  useEffect(() => {
    const controller = new AbortController();
    const snapshot = JSON.parse(key) as {
      filters: Filters;
      profile: Profile | null;
    };
    const query = new URLSearchParams({ ...snapshot.filters });
    request<{ ready: boolean; data: InsightsData | null }>(
      (snapshot.profile ? "/personalized-insights?" : "/insights?") + query,
      {
        signal: controller.signal,
        ...(snapshot.profile
          ? {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(snapshot.profile),
            }
          : {}),
      },
    )
      .then((result) => {
        if (!controller.signal.aborted) {
          setData(result.data);
          setLoaded(true);
        }
      })
      .catch((reason) => {
        if (!controller.signal.aborted) {
          setError(reason.message);
          setLoaded(true);
        }
      });
    return () => controller.abort();
  }, [key]);
  return (
    <main className="secondary-page">
      <div className="page-heading">
        <h1>نظرة على الفرص</h1>
        <p>
          توزيع الوجهات والتمويل وفق الفلاتر والتخصيص الحاليين، من آخر لقطة
          تحليل محفوظة.
        </p>
      </div>
      {error ? (
        <p role="alert" className="error-copy">
          {error}
        </p>
      ) : !loaded ? (
        <div className="loading-state">جارٍ تحميل التحليلات…</div>
      ) : !data ? (
        <div className="empty-state">
          <BarChart3 size={42} />
          <h2>التحليلات قيد التجهيز</h2>
          <p>
            تظهر هنا نتائج تحليل البيانات المخزنة بعد اكتمال أول تشغيل
            للتحليلات.
          </p>
        </div>
      ) : (
        <>
          <div className="insight-summary">
            <div>
              <strong>{number(data.confirmed_opportunities)}</strong>
              <span>فرصة بهوية موحّدة</span>
            </div>
            <div>
              <strong>{number(data.total_listings)}</strong>
              <span>إعلان ضمن الاختيارات</span>
            </div>
            <p>
              <RefreshCw size={16} />
              آخر تحليل: {formatDate(data.computed_at, true)}
              <small>
                هذه الأرقام تغطي البيانات المجموعة، وليست حصرًا لجميع منح العالم.
              </small>
            </p>
          </div>
          <div className="charts-grid">
            <BarPanel
              title="الوجهات ضمن اختياراتك"
              values={data.by_country
                .slice(0, 10)
                .map((r) => ({
                  label: countryName(r.country),
                  value: r.opportunities,
                }))}
            />
            <BarPanel
              title="الفرص حسب المرحلة"
              values={data.by_degree.map((r) => ({
                label: degreeLabels[r.degree] || r.degree,
                value: r.opportunities,
              }))}
            />
            <BarPanel
              title="توزيع التمويل"
              values={data.by_funding.map((r) => ({
                label: fundingLabels[r.funding] || r.funding,
                value: r.opportunities,
              }))}
            />
          </div>
          <section className="deadlines-panel">
            <h2>
              <CalendarDays size={22} />
              مواعيد موثقة قادمة
            </h2>
            {data.upcoming_deadlines.length ? (
              data.upcoming_deadlines.map((r) => (
                <button key={r.id} onClick={() => onOpen(r.id)}>
                  <span dir="auto">{r.title}</span>
                  <strong>{formatDate(r.deadline)}</strong>
                </button>
              ))
            ) : (
              <p className="muted">
                ما في مواعيد رسمية مؤكدة ضمن نطاق التحليل الحالي.
              </p>
            )}
          </section>
        </>
      )}
    </main>
  );
}

function BarPanel({
  title,
  values,
}: {
  title: string;
  values: { label: string; value: number }[];
}) {
  const maximum = Math.max(1, ...values.map((v) => v.value));
  return (
    <section className="bar-panel">
      <h2>{title}</h2>
      {values.map((row) => (
        <div className="bar-row" key={row.label}>
          <div>
            <span>{row.label}</span>
            <strong>{number(row.value)}</strong>
          </div>
          <div className="bar-track">
            <span style={{ width: `${(row.value / maximum) * 100}%` }} />
          </div>
        </div>
      ))}
      {!values.length && <p className="muted">لا تتوفر بيانات كافية.</p>}
    </section>
  );
}
