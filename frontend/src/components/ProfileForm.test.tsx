import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { ProfileForm } from "./ProfileForm";

HTMLDialogElement.prototype.showModal = function () {
  this.open = true;
};
afterEach(cleanup);

describe("optional student profile", () => {
  it("submits nationality, GPA basis and intended degree through named controls", () => {
    const submit = vi.fn();
    render(
      <ProfileForm
        profile={null}
        metadata={{
          countries: [{ code: "PS", name: "Palestine" }],
          fields: [],
          degrees: ["master"],
        }}
        onSubmit={submit}
        onClose={() => {}}
      />,
    );
    fireEvent.change(screen.getByLabelText("الجنسية", { exact: true }), {
      target: { value: "PS" },
    });
    fireEvent.change(
      screen.getByLabelText("المرحلة التي تريد دراستها", { exact: true }),
      { target: { value: "master" } },
    );
    fireEvent.change(screen.getByLabelText("التخصص المطلوب", { exact: true }), {
      target: { value: "engineering" },
    });
    fireEvent.change(screen.getByLabelText("مقياس المعدل", { exact: true }), {
      target: { value: "4" },
    });
    fireEvent.change(
      screen.getByLabelText("المعدل الأكاديمي", { exact: true }),
      { target: { value: "3.7" } },
    );
    fireEvent.submit(screen.getByRole("form", { name: "معلومات الطالب" }));
    expect(submit).toHaveBeenCalledWith({
      nationality: "PS",
      degree: "master",
      field: "engineering",
      gpa: 3.7,
      gpa_scale: 4,
      preferred_countries: [],
    });
  });

  it("accepts a global destination and a custom GPA basis", () => {
    const submit = vi.fn();
    render(
      <ProfileForm
        profile={{
          nationality: "PS",
          degree: "master",
          field: "engineering",
          gpa: 17,
          gpa_scale: 20,
          preferred_countries: [],
        }}
        metadata={{
          countries: [
            { code: "PS", name: "Palestine" },
            { code: "JP", name: "Japan" },
          ],
          fields: [],
          degrees: ["master"],
        }}
        onSubmit={submit}
        onClose={() => {}}
      />,
    );
    expect(screen.getByLabelText("مقياس معدل آخر")).toHaveValue(20);
    fireEvent.change(screen.getByLabelText("إضافة دولة مفضلة"), {
      target: { value: "JP" },
    });
    fireEvent.submit(screen.getByRole("form", { name: "معلومات الطالب" }));
    expect(submit).toHaveBeenCalledWith(
      expect.objectContaining({
        gpa: 17,
        gpa_scale: 20,
        preferred_countries: ["JP"],
      }),
    );
  });
});
