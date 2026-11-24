import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { renderWithProviders } from "@/test/render";

const login = vi.fn().mockResolvedValue(undefined);
vi.mock("@/lib/auth", () => ({ useAuth: () => ({ me: null, login }) }));
let siteKey: string | null = "site-key";
vi.mock("@/lib/api", () => ({ api: () => Promise.resolve({ recaptcha_site_key: siteKey }), ApiError: class extends Error {} }));

import { LoginPage } from "./LoginPage";

describe("Đăng nhập", () => {
  beforeEach(() => { login.mockClear(); });

  it("khi bật reCAPTCHA: chưa đánh dấu thì không gửi; đánh dấu xong gửi kèm mã", async () => {
    siteKey = "site-key";
    let cb: ((t: string) => void) | undefined;
    window.grecaptcha = { render: (_el, o) => { cb = o.callback; return 1; }, reset: vi.fn() };
    renderWithProviders(<LoginPage />);
    expect(await screen.findByTestId("recaptcha")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Tên đăng nhập"), "chutich");
    await userEvent.type(screen.getByLabelText("Mật khẩu"), "Mat-khau@1");
    await userEvent.click(screen.getByRole("button", { name: "Đăng nhập" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Tôi không phải người máy");
    expect(login).not.toHaveBeenCalled();
    cb?.("token-123");
    await userEvent.click(screen.getByRole("button", { name: "Đăng nhập" }));
    expect(login).toHaveBeenCalledWith("chutich", "Mat-khau@1", "", "token-123");
  });

  it("khi tắt reCAPTCHA (mạng nội bộ) không hiện ô xác minh", async () => {
    siteKey = null;
    renderWithProviders(<LoginPage />);
    await userEvent.type(await screen.findByLabelText("Tên đăng nhập"), "canbo1");
    await userEvent.type(screen.getByLabelText("Mật khẩu"), "x");
    await userEvent.click(screen.getByRole("button", { name: "Đăng nhập" }));
    expect(screen.queryByTestId("recaptcha")).not.toBeInTheDocument();
    expect(login).toHaveBeenCalledWith("canbo1", "x", "", undefined);
  });
});
