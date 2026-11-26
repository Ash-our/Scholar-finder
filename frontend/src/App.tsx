import { lazy, Suspense, useEffect, useState } from "react";
import type { MouseEvent as ReactMouseEvent } from "react";
import {
  BookOpen,
  Compass,
  SlidersHorizontal,
  Map as MapIcon,
  List,
  X,
  RefreshCw,
  Activity,
  FilterX,
} from "lucide-react";
import {
  readProfile,
  request,
  storeProfile,
  useCatalogue,
  useCountryOverview,
} from "./api";
import type { Filters, MapGroup, Metadata, Profile } from "./types";
import { countryName, formatDate, number } from "./labels";
import { FiltersBar } from "./components/FiltersBar";
import { ScholarshipList } from "./components/ScholarshipList";
import { ProfileForm } from "./components/ProfileForm";
import { ScholarshipDetail } from "./components/ScholarshipDetail";
import { Insights } from "./components/Insights";
import { SourceActivity } from "./components/SourceActivity";
import { LiveActivity } from "./components/LiveActivity";

const ScholarshipMap = lazy(() => import("./components/ScholarshipMap"));
const INITIAL_FILTERS: Filters = {
  q: "",
  country: "",
  degree: "",
  field: "",
  funding: "",
  status: "discover",
  sort: "deadline",
  placement: "",
  bbox: "",
};

export default function App() {
  const [tab, setTab] = useState<"explore" | "insights" | "sources" | "live">(
    "explore",
  );
  const [filters, setFilters] = useState<Filters>(INITIAL_FILTERS);
  const [profile, setProfile] = useState<Profile | null>(readProfile);
  const [metadata, setMetadata] = useState<Metadata | null>(null);
  const [profileOpen, setProfileOpen] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [mobileView, setMobileView] = useState<"map" | "list">("map");
  const [page, setPage] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const [mapFocus, setMapFocus] = useState<{
    sequence: number;
    country: string;
  } | null>(null);
  const { data, error, loading } = useCatalogue(
    filters,
    profile,
    page,
    refresh,
  );
  const countryOverview = useCountryOverview(filters, profile);
  useEffect(() => {
    const controller = new AbortController();
    request<Metadata>("/meta", { signal: controller.signal })
      .then(setMetadata)
      .catch(() => {});
    return () => controller.abort();
  }, []);
  function changeFilters(next: Partial<Filters>) {
    if (next.country && next.country !== filters.country)
      setMapFocus((previous) => ({
        sequence: (previous?.sequence || 0) + 1,
        country: next.country!,
      }));
    setFilters((previous) => ({ ...previous, ...next }));
    setPage(0);
  }
  function personalize(next: Profile) {
    setProfile(next);
    storeProfile(next);
    setPage(0);
    setProfileOpen(false);
    setTab("explore");
  }
  function clearProfile() {
    setProfile(null);
    storeProfile(null);
    setPage(0);
  }
  function selectGroup(group: MapGroup) {
    changeFilters({ country: group.country, placement: group.id, bbox: "" });
  }
  function clearFilters() {
    setFilters(INITIAL_FILTERS);
    setProfile(null);
    storeProfile(null);
    setPage(0);
  }
  function showWorld() {
    changeFilters({ country: "", placement: "", bbox: "" });
    setMapFocus((previous) => ({
      sequence: (previous?.sequence || 0) + 1,
      country: "",
    }));
  }
  function backgroundClick(event: ReactMouseEvent<HTMLDivElement>) {
    if (tab !== "explore" || profileOpen || selectedId) return;
    const target = event.target as HTMLElement;
    if (
      target.closest(
        "button,a,input,select,textarea,label,summary,dialog,[role='search'],.leaflet-container,.results-pane,.active-filters,.discovery-notice,.mobile-view-switch",
      )
    )
      return;
    clearFilters();
  }
  const university = filters.placement
    ? (countryOverview?.groups || data?.map.groups || []).find(
        (group) => group.id === filters.placement,
      )
    : null;
  const hasFilters =
    !!profile ||
    Object.entries(INITIAL_FILTERS).some(
      ([key, value]) => filters[key as keyof Filters] !== value,
    );
  return (
    <div
      className={`app-shell ${tab === "explore" ? "is-exploring" : ""}`}
      dir="rtl"
      onClick={backgroundClick}
    >
      <header className="app-header">
        <button
          className="brand"
          onClick={() => setTab("explore")}
          aria-label="خريطة المنح، الصفحة الرئيسية"
        >
          <span className="brand-mark">
            <BookOpen />
            <Compass />
          </span>
          <strong>خريطة المنح</strong>
        </button>
        <nav aria-label="التنقل الرئيسي">
          <button
            className={tab === "explore" ? "active" : ""}
            aria-current={tab === "explore" ? "page" : undefined}
            onClick={() => setTab("explore")}
          >
            استكشف المنح
          </button>
          <button
            className={tab === "insights" ? "active" : ""}
            aria-current={tab === "insights" ? "page" : undefined}
            onClick={() => setTab("insights")}
          >
            نظرة على الفرص
          </button>
          <button
            className={tab === "sources" ? "active" : ""}
            aria-current={tab === "sources" ? "page" : undefined}
            onClick={() => setTab("sources")}
          >
            نشاط المصادر
          </button>
          <button
            className={tab === "live" ? "active" : ""}
            aria-current={tab === "live" ? "page" : undefined}
            onClick={() => setTab("live")}
          >
            <Activity size={16} />
            البث المباشر
          </button>
        </nav>
        <button
          className="button outline profile-button"
          onClick={() => setProfileOpen(true)}
        >
          <SlidersHorizontal size={20} />
          {profile ? "تعديل معلوماتي" : "خصص فرصك"}
        </button>
      </header>
      {metadata?.mode === "replay" && (
        <div className="replay-banner" role="status">
          وضع إعادة البث: هذه بيانات لقطة محفوظة، وتوقيت الأحداث تجريبي.
        </div>
      )}
      {tab === "explore" ? (
        <main className="explore-page">
          <section className="intro sr-only">
            <h1>فرصتك القادمة، على الخريطة</h1>
            <p>
              استكشف المنح الدراسية حول العالم، وخصص النتائج حسب دراستك وطموحك.
            </p>
          </section>
          <FiltersBar
            filters={filters}
            metadata={metadata}
            onChange={changeFilters}
          />
          {data && filters.status === "discover" && (
            <p className="discovery-notice">
              <strong>
                {number(data.status_counts.open || 0)} مفتوحة موثّقة
              </strong>
              <span>
                نعرض أيضًا الفرص المحتملة، مع تمييز ما يحتاج تأكيد الموعد
                والشروط. المغلقة مستبعدة.
              </span>
              <button
                className="text-button"
                onClick={() => changeFilters({ status: "open" })}
              >
                المفتوحة الموثّقة فقط
              </button>
            </p>
          )}
          {hasFilters && (
            <div className="active-filters" aria-label="الفلاتر النشطة">
              {profile && (
                <span>
                  نتائج مخصصة حسب معلوماتك{" "}
                  <button onClick={clearProfile} aria-label="إلغاء التخصيص">
                    <X size={15} />
                  </button>
                </span>
              )}
              {filters.country && (
                <span>
                  {countryName(filters.country)}
                  <button
                    onClick={() =>
                      changeFilters({ country: "", placement: "", bbox: "" })
                    }
                    aria-label="إزالة فلتر الدولة"
                  >
                    <X size={15} />
                  </button>
                </span>
              )}
              {filters.placement && (
                <span>
                  <span dir="auto">
                    {university?.name || "الجامعة المحددة"}
                  </span>
                  <button
                    onClick={() => changeFilters({ placement: "" })}
                    aria-label="إزالة فلتر الجامعة"
                  >
                    <X size={15} />
                  </button>
                </span>
              )}
              {filters.bbox && (
                <span>
                  نطاق الخريطة المحدد
                  <button
                    onClick={() => changeFilters({ bbox: "" })}
                    aria-label="إلغاء نطاق الخريطة"
                  >
                    <X size={15} />
                  </button>
                </span>
              )}
              <button
                className="clear-all-filters"
                onClick={clearFilters}
                aria-label="مسح جميع الفلاتر"
              >
                <FilterX size={15} />
                مسح الفلاتر
              </button>
            </div>
          )}
          <div className="mobile-view-switch" aria-label="طريقة عرض النتائج">
            <button
              aria-pressed={mobileView === "map"}
              onClick={() => setMobileView("map")}
            >
              <MapIcon size={17} />
              الخريطة
            </button>
            <button
              aria-pressed={mobileView === "list"}
              onClick={() => setMobileView("list")}
            >
              <List size={17} />
              القائمة
            </button>
          </div>
          <div className="workspace">
            <div
              className={
                mobileView !== "list"
                  ? "list-area mobile-pane-hidden"
                  : "list-area"
              }
            >
              <ScholarshipList
                data={data}
                loading={loading}
                error={error}
                sort={filters.sort}
                page={page}
                onSort={(sort) => changeFilters({ sort })}
                onPage={setPage}
                onOpen={setSelectedId}
                onHover={setHoveredId}
                onUnverified={() => changeFilters({ status: "unverified" })}
                onReset={clearFilters}
                onRetry={() => setRefresh((value) => value + 1)}
              />
            </div>
            <div
              className={
                mobileView !== "map"
                  ? "map-area mobile-pane-hidden"
                  : "map-area"
              }
            >
              <Suspense
                fallback={
                  <div className="map-placeholder">جارٍ تحميل الخريطة…</div>
                }
              >
                <ScholarshipMap
                  data={data?.map}
                  overview={countryOverview}
                  selectedCountry={filters.country}
                  selectedPlacement={filters.placement}
                  focusRequest={mapFocus}
                  hoveredId={hoveredId}
                  onCountry={(country) => {
                    changeFilters({ country, placement: "", bbox: "" });
                    setMobileView("map");
                  }}
                  onSelect={selectGroup}
                  onClear={clearFilters}
                  onWorld={showWorld}
                />
              </Suspense>
            </div>
          </div>
          <footer className="explore-footer">
            <span>
              التقديم يتم عبر الجهات المانحة. التفاصيل غير المؤكدة مميزة داخل كل
              فرصة.
            </span>
            <span>
              <RefreshCw size={13} />
              {data?.last_fetched_at
                ? `آخر بيانات مجموعة: ${formatDate(data.last_fetched_at, true)}`
                : "بانتظار بيانات المصادر"}
            </span>
          </footer>
        </main>
      ) : tab === "insights" ? (
        <Insights onOpen={setSelectedId} filters={filters} profile={profile} />
      ) : tab === "live" ? (
        <LiveActivity onOpen={setSelectedId} />
      ) : (
        <SourceActivity />
      )}
      {profileOpen && (
        <ProfileForm
          profile={profile}
          metadata={metadata}
          onSubmit={personalize}
          onClose={() => setProfileOpen(false)}
        />
      )}
      {selectedId && (
        <ScholarshipDetail
          key={selectedId}
          id={selectedId}
          cached={data?.items.find((record) => record.id === selectedId)}
          onClose={() => setSelectedId(null)}
        />
      )}
    </div>
  );
}
