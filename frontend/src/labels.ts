import type { Scholarship } from "./types";

export const degreeLabels: Record<string, string> = {
  bachelor: "بكالوريوس",
  master: "ماجستير",
  phd: "دكتوراه",
  postdoc: "ما بعد الدكتوراه",
  research: "بحث علمي",
  other: "مرحلة أخرى",
};
export const fieldLabels: Record<string, string> = {
  computer_science: "علوم الحاسوب",
  engineering: "الهندسة",
  business: "الأعمال والإدارة",
  medicine: "الطب والعلوم الصحية",
  natural_sciences: "العلوم الطبيعية",
  social_sciences: "العلوم الاجتماعية",
  arts: "الآداب والفنون",
  law: "القانون",
  education: "التربية والتعليم",
  agriculture: "الزراعة والبيئة",
  all: "جميع التخصصات",
};
export const fundingLabels: Record<string, string> = {
  full: "تمويل كامل",
  partial: "تمويل جزئي",
  tuition: "رسوم دراسية",
  stipend: "مخصصات مالية",
  unknown: "التمويل غير محدد",
};
export const statusLabels: Record<string, string> = {
  discover: "الحالية والمحتملة",
  open: "مفتوح حاليًا",
  upcoming: "يفتح قريبًا",
  closed: "مغلق",
  unverified: "بحاجة تحقق",
  all: "كل الحالات",
};
const regions = new Intl.DisplayNames(["ar"], { type: "region" });
export function countryName(code: string) {
  return regions.of(code) || code;
}
export const number = (value: number) =>
  new Intl.NumberFormat("ar-u-nu-latn").format(value);
export function formatDate(
  value: string | null | undefined,
  withTime = false,
  withSeconds = false,
) {
  if (!value) return "غير متوفر";
  const date = new Date(value.length === 10 ? value + "T12:00:00Z" : value);
  if (Number.isNaN(date.valueOf())) return "غير متوفر";
  return new Intl.DateTimeFormat("ar-PS-u-nu-latn", {
    day: "numeric",
    month: "long",
    year: "numeric",
    ...(withTime ? ({ hour: "2-digit", minute: "2-digit" } as const) : {}),
    ...(withTime && withSeconds ? ({ second: "2-digit" } as const) : {}),
  }).format(date);
}
export const titleOf = (record: Scholarship) => record.title_ar || record.title;
