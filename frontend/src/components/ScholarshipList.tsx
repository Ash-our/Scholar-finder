import {
  CalendarDays,
  CheckCircle2,
  CircleHelp,
  GraduationCap,
  MapPin,
  Coins,
  SearchX,
} from "lucide-react";
import type { CatalogueResponse, Filters, Scholarship } from "../types";
import {
  countryName,
  degreeLabels,
  fundingLabels,
  formatDate,
  number,
  statusLabels,
  titleOf,
} from "../labels";

export function ScholarshipList({
  data,
  loading,
  error,
  sort,
  page,
  onSort,
  onPage,
  onOpen,
  onHover,
  onUnverified,
  onReset,
  onRetry,
}: {
  data: CatalogueResponse | null;
  loading: boolean;
  error: string;
  sort: Filters["sort"];
  page: number;
  onSort: (sort: Filters["sort"]) => void;
  onPage: (page: number) => void;
  onOpen: (id: string) => void;
  onHover: (id: string | null) => void;
  onUnverified: () => void;
  onReset: () => void;
  onRetry: () => void;
}) {
  return (
    <section
      className="results-pane"
      aria-label="قائمة المنح"
      aria-busy={loading}
    >
      <div className="results-heading">
        <div>
          <h2>
            {data ? number(data.total) : "…"} <span>نتيجة للبحث</span>
          </h2>
          {data && (
            <p>
              {number(data.status_counts.open || 0)} مفتوحة موثّقة ·{" "}
              {number(data.status_counts.unverified || 0)} بحاجة تحقق
            </p>
          )}
        </div>
        <label className="sort-select">
          <span className="sr-only">ترتيب النتائج</span>
          <select
            aria-label="ترتيب النتائج"
            value={sort}
            onChange={(e) => onSort(e.target.value as Filters["sort"])}
          >
            <option value="deadline">الأقرب موعدًا</option>
            <option value="newest">الأحدث جمعًا</option>
            <option value="added">الأحدث إضافة للنظام</option>
            <option value="title">الاسم</option>
          </select>
        </label>
      </div>
      {loading && <div className="loading-line" />}
      {error ? (
        <div className="empty-state" role="alert">
          <CircleHelp size={36} />
          <h3>تعذر تحميل الفرص</h3>
          <p>{error}</p>
          <button className="button outline" onClick={onRetry}>
            إعادة المحاولة
          </button>
        </div>
      ) : !data && loading ? (
        <div className="loading-state">جارٍ تحميل الفرص من قاعدة البيانات…</div>
      ) : data?.items.length ? (
        <div className="scholarship-rows">
          {data.items.map((record) => (
            <ScholarshipRow
              key={record.id}
              record={record}
              onOpen={onOpen}
              onHover={onHover}
            />
          ))}
        </div>
      ) : (
        <div className="empty-state">
          <SearchX size={42} />
          <h3>ما في فرص ضمن هالاختيارات</h3>
          <p>
            جرّب تغيير الفلاتر، أو استكشف الإعلانات التي ما زالت تفاصيلها بحاجة
            تحقق.
          </p>
          <button className="button primary" onClick={onUnverified}>
            استكشف فرصًا بحاجة تحقق
          </button>
          <button className="text-button" onClick={onReset}>
            إعادة ضبط الفلاتر
          </button>
        </div>
      )}
      {data && data.total > 30 && (
        <div className="pagination">
          <button
            className="button outline"
            disabled={page === 0 || loading}
            onClick={() => onPage(page - 1)}
          >
            السابق
          </button>
          <span>
            {number(page + 1)} / {number(Math.ceil(data.total / 30))}
          </span>
          <button
            className="button outline"
            disabled={(page + 1) * 30 >= data.total || loading}
            onClick={() => onPage(page + 1)}
          >
            التالي
          </button>
        </div>
      )}
      {data && data.map.unmapped_count > 0 && (
        <p className="map-footnote">
          {number(data.map.unmapped_count)} إعلان بدون موقع محدد؛ تظل متاحة في
          القائمة.
        </p>
      )}
    </section>
  );
}

function ScholarshipRow({
  record,
  onOpen,
  onHover,
}: {
  record: Scholarship;
  onOpen: (id: string) => void;
  onHover: (id: string | null) => void;
}) {
  return (
    <article
      className="scholarship-row"
      onMouseEnter={() => onHover(record.id)}
      onMouseLeave={() => onHover(null)}
    >
      <div className="row-title">
        <span className="award-icon">
          <GraduationCap size={22} />
        </span>
        <div>
          <h3 dir="auto">{titleOf(record)}</h3>
          <p className="provider" dir="auto">
            {record.provider || "الجهة غير محددة"}
          </p>
        </div>
      </div>
      <div className="row-facts">
        <p>
          <MapPin size={16} />
          <span>
            {record.countries.length
              ? record.countries.map(countryName).join("، ")
              : "الوجهة بحاجة تحديد"}
          </span>
        </p>
        <p>
          <GraduationCap size={16} />
          <span>
            {record.degrees.length
              ? record.degrees.map((d) => degreeLabels[d]).join(" / ")
              : "المرحلة غير محددة"}
          </span>
        </p>
        <p>
          <Coins size={16} />
          <span>{fundingLabels[record.funding]}</span>
        </p>
        <p>
          <CalendarDays size={16} />
          <span>
            {record.deadline
              ? formatDate(record.deadline)
              : record.open_evidence === "rolling"
                ? "مستمر أو ترشيح تلقائي · راجع التفاصيل"
                : "الموعد بحاجة تحقق"}
            {record.deadline_confidence === "estimated" ? " · تقديري" : ""}
          </span>
        </p>
      </div>
      {record.match && (
        <div className="match-explanation">
          <CheckCircle2 size={15} />
          <span>
            {record.match.reasons.slice(0, 2).join(" · ") ||
              "فرصة محتملة بحسب المعلومات المتاحة"}
          </span>
          {record.match.uncertainties.length > 0 && (
            <small>متطلبات إضافية بحاجة تحقق</small>
          )}
        </div>
      )}
      <div className="row-bottom">
        <span className={`status-label ${record.application_state}`}>
          {record.application_state === "open" ? (
            <CheckCircle2 size={15} />
          ) : (
            <CircleHelp size={15} />
          )}{" "}
          {statusLabels[record.application_state]}
        </span>
        <button
          className="button outline compact"
          onClick={() => onOpen(record.id)}
        >
          عرض التفاصيل
        </button>
      </div>
      <div className="ingestion-stamp">
        <span>
          أضيفت للنظام:{" "}
          {record.added_at
            ? formatDate(record.added_at, true)
            : "لا يوجد سجل زمني موثق"}
        </span>
        {record.updated_at && (
          <span>آخر تحديث: {formatDate(record.updated_at, true)}</span>
        )}
      </div>
    </article>
  );
}
