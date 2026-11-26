import { useState } from "react";
import {
  Search,
  MapPin,
  GraduationCap,
  Coins,
  CalendarDays,
  SlidersHorizontal,
} from "lucide-react";
import type { Filters, Metadata } from "../types";
import {
  countryName,
  degreeLabels,
  fundingLabels,
  statusLabels,
} from "../labels";

export function FiltersBar({
  filters,
  metadata,
  onChange,
}: {
  filters: Filters;
  metadata: Metadata | null;
  onChange: (value: Partial<Filters>) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div
      className={`filters-bar ${expanded ? "filters-expanded" : ""}`}
      role="search"
      aria-label="تصفية المنح"
    >
      <label className="search-field">
        <Search size={22} />
        <input
          type="search"
          value={filters.q}
          maxLength={120}
          aria-label="ابحث عن منحة أو جامعة"
          placeholder="ابحث عن منحة أو جامعة"
          onChange={(e) => onChange({ q: e.target.value })}
        />
      </label>
      <button
        className="button outline mobile-filter-toggle"
        aria-expanded={expanded}
        aria-controls="scholarship-filter-options"
        onClick={() => setExpanded((value) => !value)}
      >
        <SlidersHorizontal size={17} />
        الفلاتر
      </button>
      <div className="filter-options" id="scholarship-filter-options">
        <label className="filter-field">
          <MapPin />
          <span>
            الدولة
            <select
              aria-label="الدولة"
              value={filters.country}
              onChange={(e) =>
                onChange({ country: e.target.value, placement: "" })
              }
            >
              <option value="">كل الدول</option>
              {(metadata?.countries || [])
                .slice()
                .sort((a, b) =>
                  countryName(a.code).localeCompare(countryName(b.code), "ar"),
                )
                .map((c) => (
                  <option key={c.code} value={c.code}>
                    {countryName(c.code)}
                  </option>
                ))}
            </select>
          </span>
        </label>
        <label className="filter-field">
          <GraduationCap />
          <span>
            الدرجة الدراسية
            <select
              aria-label="الدرجة الدراسية"
              value={filters.degree}
              onChange={(e) => onChange({ degree: e.target.value })}
            >
              <option value="">كل الدرجات</option>
              {Object.entries(degreeLabels).map(([key, label]) => (
                <option value={key} key={key}>
                  {label}
                </option>
              ))}
            </select>
          </span>
        </label>
        <label className="filter-field">
          <Coins />
          <span>
            نوع التمويل
            <select
              aria-label="نوع التمويل"
              value={filters.funding}
              onChange={(e) => onChange({ funding: e.target.value })}
            >
              <option value="">كل أنواع التمويل</option>
              {Object.entries(fundingLabels).map(([key, label]) => (
                <option value={key} key={key}>
                  {label}
                </option>
              ))}
            </select>
          </span>
        </label>
        <label className="filter-field">
          <CalendarDays />
          <span>
            حالة التقديم
            <select
              aria-label="حالة التقديم"
              value={filters.status}
              onChange={(e) =>
                onChange({ status: e.target.value as Filters["status"] })
              }
            >
              {Object.entries(statusLabels).map(([key, label]) => (
                <option value={key} key={key}>
                  {label}
                </option>
              ))}
            </select>
          </span>
        </label>
      </div>
    </div>
  );
}
