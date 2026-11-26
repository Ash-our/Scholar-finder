import { useEffect, useState } from "react";
import {
  CalendarDays,
  ExternalLink,
  MapPin,
  GraduationCap,
  Coins,
  CircleHelp,
  CheckCircle2,
} from "lucide-react";
import type { Scholarship } from "../types";
import { request } from "../api";
import {
  countryName,
  degreeLabels,
  fieldLabels,
  formatDate,
  fundingLabels,
  statusLabels,
  titleOf,
} from "../labels";
import { Dialog } from "./Dialog";

export function ScholarshipDetail({
  id,
  cached,
  onClose,
}: {
  id: string;
  cached?: Scholarship;
  onClose: () => void;
}) {
  const [record, setRecord] = useState<Scholarship | undefined>(cached);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    request<Scholarship>("/scholarships/" + encodeURIComponent(id), {
      signal: controller.signal,
    })
      .then((value) => {
        if (!controller.signal.aborted)
          setRecord((previous) => ({ ...value, match: previous?.match }));
      })
      .catch((reason) => {
        if (!controller.signal.aborted) setError(reason.message);
      });
    return () => controller.abort();
  }, [id]);
  return (
    <Dialog title="تفاصيل المنحة" onClose={onClose} wide>
      {error ? (
        <p role="alert" className="error-copy">
          {error}
        </p>
      ) : !record ? (
        <p>جارٍ تحميل التفاصيل…</p>
      ) : (
        <>
          <div className="detail-title">
            <span className="award-icon large">
              <GraduationCap size={28} />
            </span>
            <div>
              <h3 dir="auto">{titleOf(record)}</h3>
              <p dir="auto">{record.provider}</p>
            </div>
          </div>
          <div className="detail-status">
            <span className={`status-label ${record.application_state}`}>
              {statusLabels[record.application_state]}
            </span>
            <span>{record.cycle || "دورة التقديم غير محددة"}</span>
          </div>
          <div className="detail-facts">
            <div>
              <MapPin />
              <span>الوجهة</span>
              <strong>
                {record.countries.map(countryName).join("، ") || "غير محددة"}
              </strong>
            </div>
            <div>
              <GraduationCap />
              <span>المرحلة</span>
              <strong>
                {record.degrees.map((d) => degreeLabels[d]).join("، ") ||
                  "غير محددة"}
              </strong>
            </div>
            <div>
              <Coins />
              <span>التمويل</span>
              <strong>{fundingLabels[record.funding]}</strong>
            </div>
            <div>
              <CalendarDays />
              <span>موعد التقديم</span>
              <strong>
                {record.deadline ? formatDate(record.deadline) : "بحاجة تحقق"}
              </strong>
            </div>
          </div>
          {record.match && (
            <section className="detail-section match-panel">
              <h4>لماذا ظهرت لك هذه الفرصة؟</h4>
              {record.match.reasons.map((reason) => (
                <p className="reason" key={reason}>
                  <CheckCircle2 size={17} />
                  {reason}
                </p>
              ))}
              {record.match.uncertainties.map((reason) => (
                <p className="reason muted" key={reason}>
                  <CircleHelp size={17} />
                  {reason}
                </p>
              ))}
              <p className="form-hint">
                الترتيب يعبّر عن توافق التفضيلات، ولا يمثل احتمال القبول.
              </p>
            </section>
          )}
          <section className="detail-section">
            <h4>التمويل والمجالات</h4>
            <p dir="auto">
              {record.description ||
                "تفاصيل التغطية غير متوفرة في المصدر المجموع."}
            </p>
            <p>
              {record.fields.map((f) => fieldLabels[f] || f).join("، ") ||
                "التخصصات بحاجة تحقق من المصدر"}
            </p>
          </section>
          <section className="detail-section">
            <h4>شروط التقديم</h4>
            <dl className="requirements">
              <div>
                <dt>الجنسية</dt>
                <dd>
                  {record.nationalities.includes("*")
                    ? "جنسيات متعددة؛ راجع الاستثناءات في المصدر"
                    : record.nationalities.map(countryName).join("، ") ||
                      "غير محددة"}
                </dd>
              </div>
              <div>
                <dt>الحد الأدنى للمعدل</dt>
                <dd>
                  {record.minimum_gpa !== null
                    ? `${record.minimum_gpa} من ${record.gpa_scale}`
                    : "لم يذكر حد واضح"}
                </dd>
              </div>
              {record.excluded_nationalities.length > 0 && (
                <div>
                  <dt>استثناءات الجنسية</dt>
                  <dd>
                    {record.excluded_nationalities.map(countryName).join("، ")}
                  </dd>
                </div>
              )}
            </dl>
            <details>
              <summary>قراءة نص الشروط من المصدر</summary>
              <p className="original-text" dir="auto">
                {record.eligibility_text ||
                  "نص الشروط غير متوفر. راجع الصفحة الأصلية."}
              </p>
            </details>
          </section>
          <section className="detail-section">
            <h4>الموقع على الخريطة</h4>
            {record.placements.length ? (
              record.placements.map((place) => (
                <p key={place.id} className="location-detail">
                  <MapPin size={16} />
                  <span dir="auto">{place.name}</span>
                  <small>
                    {place.precision === "country"
                      ? "نطاق دولة؛ لا يحدد جامعة بعينها"
                      : place.precision === "city"
                        ? "موقع مدينة تقريبي"
                        : "موقع الحرم"}{" "}
                    ·{" "}
                    <a href={place.source_url} target="_blank" rel="noreferrer">
                      مرجع الموقع
                    </a>
                  </small>
                </p>
              ))
            ) : (
              <p>ما في موقع موثوق متاح لهذه الفرصة بعد.</p>
            )}
          </section>
          <div className="detail-actions">
            {record.official_url && (
              <a
                className="button primary"
                href={record.official_url}
                target="_blank"
                rel="noreferrer"
              >
                زيارة الصفحة الرسمية
                <ExternalLink size={17} />
              </a>
            )}
            <a
              className="button outline"
              href={record.source_url}
              target="_blank"
              rel="noreferrer"
            >
              عرض الإعلان الأصلي
              <ExternalLink size={17} />
            </a>
          </div>
        </>
      )}
    </Dialog>
  );
}
