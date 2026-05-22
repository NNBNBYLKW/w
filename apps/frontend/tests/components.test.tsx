import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { ActionButton } from "../src/shared/ui/components";
import { t } from "../src/shared/text";
import { LocaleProvider } from "../src/shared/text/LocaleProvider";
import { AppSidebar } from "../src/app/shell/AppSidebar";

function renderWithProviders(ui: React.ReactElement, { route = "/" } = {}) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <LocaleProvider defaultLocale="en">
        {ui}
      </LocaleProvider>
    </MemoryRouter>
  );
}

describe("ActionButton", () => {
  it("renders a primary button", () => {
    render(<ActionButton variant="primary">Click me</ActionButton>);
    const btn = screen.getByRole("button", { name: "Click me" });
    expect(btn).toBeInTheDocument();
    expect(btn.className).toContain("primary");
  });

  it("renders a secondary button", () => {
    render(<ActionButton variant="secondary">Cancel</ActionButton>);
    const btn = screen.getByRole("button", { name: "Cancel" });
    expect(btn.className).toContain("secondary");
  });

  it("renders a danger button", () => {
    render(<ActionButton variant="danger">Delete</ActionButton>);
    const btn = screen.getByRole("button", { name: "Delete" });
    expect(btn.className).toContain("danger");
  });

  it("disables when disabled prop is set", () => {
    render(<ActionButton disabled>Can't click</ActionButton>);
    expect(screen.getByRole("button")).toBeDisabled();
  });

  it("renders small size", () => {
    render(<ActionButton size="sm">Small</ActionButton>);
    const btn = screen.getByRole("button");
    expect(btn.className).toContain("sm");
  });
});

describe("AppSidebar", () => {
  it("renders brand and navigation", () => {
    renderWithProviders(<AppSidebar />);
    expect(screen.getByText("W")).toBeInTheDocument();
    expect(screen.getByRole("navigation")).toBeInTheDocument();
  });

  it("renders all navigation groups", () => {
    renderWithProviders(<AppSidebar />);
    expect(screen.getByText(t("shell.sidebar.groups.main"))).toBeInTheDocument();
    expect(screen.getByText(t("shell.sidebar.groups.fileLibrary"))).toBeInTheDocument();
    expect(screen.getByText(t("shell.sidebar.groups.manage"))).toBeInTheDocument();
    expect(screen.getByText(t("shell.sidebar.groups.refind"))).toBeInTheDocument();
    expect(screen.getByText(t("shell.sidebar.groups.system"))).toBeInTheDocument();
  });

  it("renders key nav links", () => {
    renderWithProviders(<AppSidebar />);
    expect(screen.getByText(t("navigation.items.home"))).toBeInTheDocument();
    expect(screen.getByText(t("navigation.items.browseAll"))).toBeInTheDocument();
    expect(screen.getByText(t("navigation.items.search"))).toBeInTheDocument();
  });

  it("expands media category when clicked", async () => {
    renderWithProviders(<AppSidebar />);
    const mediaBtn = screen.getByRole("button", { name: t("navigation.items.browseMedia") });
    expect(mediaBtn).toBeInTheDocument();
    expect(mediaBtn.getAttribute("aria-expanded")).toBe("false");
    mediaBtn.click();
    await waitFor(() => {
      expect(mediaBtn.getAttribute("aria-expanded")).toBe("true");
    });
  });

  it("auto-expands media when on a media category route", () => {
    renderWithProviders(<AppSidebar />, { route: "/browse-v2?domain=media&category=movie" });
    // Parent is expanded because child is active
    const mediaBtn = screen.getByRole("button", { name: t("navigation.items.browseMedia") });
    expect(mediaBtn.getAttribute("aria-expanded")).toBe("true");
  });
});
