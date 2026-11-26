import { useState } from "react";
import type { FormEvent } from "react";
import { SlidersHorizontal } from "lucide-react";
import type { Degree, Metadata, Profile } from "../types";
import { countryName, degreeLabels, fieldLabels } from "../labels";
import { Dialog } from "./Dialog";

export function ProfileForm({
  profile,
  metadata,
  onSubmit,
  onClose,
}: {
  profile: Profile | null;
  metadata: Metadata | null;
  onSubmit: (value: Profile) => void;
  onClose: () => void;
}) {
  const [nationality, setNationality] = useState(profile?.nationality || "");
  const [gpa, setGpa] = useState(profile?.gpa?.toString() || "");
  const [scale, setScale] = useState(profile?.gpa_scale || 100);
  const [customScale, setCustomScale] = useState(
    ![100, 4, 5].includes(profile?.gpa_scale || 100),
  );
  const [field, setField] = useState(profile?.field || "");
  const [degree, setDegree] = useState(profile?.degree || "");
  const [preferred, setPreferred] = useState(
    profile?.preferred_countries || [],
  );
  const [error, setError] = useState("");
  const countries = (metadata?.countries || [])
    .slice()
    .sort((a, b) =>
      countryName(a.code).localeCompare(countryName(b.code), "ar"),
    );
  function submit(event: FormEvent) {
    event.preventDefault();
    if (!nationality || !field || !degree) {
      setError("اختر الجنسية والتخصص والمرحلة الدراسية");
      return;
    }
    const value = gpa.trim() === "" ? null : Number(gpa);
    if (!Number.isFinite(scale) || scale <= 0 || scale > 1000) {
      setError("أدخل مقياس معدل أكبر من صفر وحتى 1000");
      return;
    }
    if (preferred.length > 30) {
      setError("اختر حتى 30 دولة مفضلة");
      return;
    }
    if (
      value !== null &&
      (!Number.isFinite(value) || value < 0 || value > scale)
    ) {
      setError("أدخل معدلًا صحيحًا ضمن المقياس المحدد");
      return;
    }
    onSubmit({
      nationality,
      gpa: value,
      gpa_scale: scale,
      field,
      degree: degree as Degree,
      preferred_countries: preferred,
    });
  }
  return (
    <Dialog title="فرص أقرب لطموحك" onClose={onClose}>
      <p className="dialog-intro">
        عرّفنا على دراستك وتفضيلاتك لنرتب الفرص حسب المعلومات المتاحة. تظل بعض
        الشروط بحاجة تحقق من المصدر.
      </p>
      <form
        onSubmit={submit}
        className="profile-form"
        aria-label="معلومات الطالب"
      >
        <div className="form-grid">
          <label>
            الجنسية
            <select
              aria-label="الجنسية"
              value={nationality}
              onChange={(e) => setNationality(e.target.value)}
              required
            >
              <option value="">اختر الجنسية</option>
              {countries.map((c) => (
                <option key={c.code} value={c.code}>
                  {countryName(c.code)}
                </option>
              ))}
            </select>
          </label>
          <label>
            المرحلة التي تريد دراستها
            <select
              aria-label="المرحلة التي تريد دراستها"
              value={degree}
              onChange={(e) => setDegree(e.target.value)}
              required
            >
              <option value="">اختر المرحلة</option>
              {(metadata?.degrees || ["bachelor", "master", "phd"]).map(
                (key) => (
                  <option key={key} value={key}>
                    {degreeLabels[key]}
                  </option>
                ),
              )}
            </select>
          </label>
          <label className="full-width">
            التخصص المطلوب
            <select
              aria-label="التخصص المطلوب"
              value={field}
              onChange={(e) => setField(e.target.value)}
              required
            >
              <option value="">اختر التخصص</option>
              {Object.entries(fieldLabels)
                .filter(([key]) => key !== "all")
                .map(([key, label]) => (
                  <option key={key} value={key}>
                    {label}
                  </option>
                ))}
            </select>
          </label>
          <label>
            المعدل الأكاديمي
            <input
              aria-label="المعدل الأكاديمي"
              type="number"
              step="any"
              min="0"
              max={scale}
              value={gpa}
              placeholder="أدخل معدلك"
              onChange={(e) => setGpa(e.target.value)}
              inputMode="decimal"
            />
          </label>
          <label>
            مقياس المعدل
            <select
              aria-label="مقياس المعدل"
              value={customScale ? "custom" : scale}
              onChange={(e) => {
                setCustomScale(e.target.value === "custom");
                if (e.target.value !== "custom")
                  setScale(Number(e.target.value));
              }}
            >
              <option value={100}>من 100</option>
              <option value={4}>من 4</option>
              <option value={5}>من 5</option>
              <option value="custom">مقياس آخر</option>
            </select>
          </label>
          {customScale && (
            <label className="full-width">
              مقياس معدل آخر
              <input
                aria-label="مقياس معدل آخر"
                type="number"
                min="0.01"
                max="1000"
                step="any"
                required
                value={Number.isFinite(scale) ? scale : ""}
                onChange={(e) => setScale(e.target.valueAsNumber)}
              />
            </label>
          )}
        </div>
        <fieldset>
          <legend>
            الدول المفضلة <span className="muted">اختياري</span>
          </legend>
          <p className="form-hint">
            الدول المختارة ترفع ترتيب الفرص، ولا تستبعد الدول الأخرى.
          </p>
          <label>
            إضافة دولة مفضلة
            <select
              aria-label="إضافة دولة مفضلة"
              value=""
              disabled={preferred.length >= 30}
              onChange={(e) => {
                if (e.target.value)
                  setPreferred((previous) => [
                    ...new Set([...previous, e.target.value]),
                  ]);
              }}
            >
              <option value="">اختر من جميع الدول</option>
              {countries
                .filter((c) => !preferred.includes(c.code))
                .map((c) => (
                  <option key={c.code} value={c.code}>
                    {countryName(c.code)}
                  </option>
                ))}
            </select>
          </label>
          <div className="country-choices">
            {[
              ...new Set([
                "DE",
                "GB",
                "NL",
                "CH",
                "TR",
                "US",
                "CA",
                "AU",
                "FR",
                "IT",
                "CN",
                "PS",
                ...preferred,
              ]),
            ].map((code) => (
              <label
                key={code}
                className={
                  preferred.includes(code) ? "choice selected" : "choice"
                }
              >
                <input
                  type="checkbox"
                  checked={preferred.includes(code)}
                  onChange={(e) =>
                    setPreferred(
                      e.target.checked
                        ? [...preferred, code]
                        : preferred.filter((c) => c !== code),
                    )
                  }
                />
                {countryName(code)}
              </label>
            ))}
          </div>
        </fieldset>
        {error && (
          <p role="alert" className="error-copy">
            {error}
          </p>
        )}
        <button className="button primary form-submit" type="submit">
          <SlidersHorizontal size={18} />
          اعرض الفرص المناسبة
        </button>
        <p className="form-hint centered">
          تُحفظ معلوماتك في جلسة المتصفح الحالية، ولا تُرسل إلى الجهات المانحة.
        </p>
      </form>
    </Dialog>
  );
}
