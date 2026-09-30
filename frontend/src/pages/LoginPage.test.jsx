import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { Disclaimer } from "../components/ui";
import LoginPage from "../pages/LoginPage";
import { AuthProvider } from "../context/AuthContext";

describe("interface building blocks", () => {
  it("shows the sign-in form", () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>
    );
    expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.getByLabelText("Email, staff ID, or matriculation number")).toBeInTheDocument();
  });

  it("shows the academic judgement notice", () => {
    render(<Disclaimer />);
    expect(screen.getByText(/do not replace professional academic judgement/i)).toBeInTheDocument();
  });
});
