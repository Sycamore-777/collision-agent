import { MemoryRouter } from "react-router-dom";
import { fireEvent, render, screen } from "@testing-library/react";

import App from "./App";
import { MarkdownView } from "./components/MarkdownView";

describe("App", () => {
  it("renders the command task entry by default", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>
    );

    expect(screen.getByRole("heading", { name: "任务指令台" })).toBeInTheDocument();
    expect(screen.getByText("ORBITAL SAFETY CONSOLE")).toBeInTheDocument();
    expect(screen.getByLabelText("需求说明")).toBeInTheDocument();
    expect(screen.getByText("高级设置")).toBeInTheDocument();
    expect(screen.getByText("内联载荷")).not.toBeVisible();

    fireEvent.change(screen.getByLabelText("需求说明"), {
      target: { value: "请评估这次会合风险。" }
    });
    expect(screen.queryByText("需求草稿")).not.toBeInTheDocument();
  });

  it("renders markdown content instead of raw markdown text", () => {
    render(
      <MarkdownView
        content={"## 原因\n- **Pc** 达到关注阈值\n\n`collision_probability` 需要复核。"}
      />
    );

    expect(screen.getByRole("heading", { name: "原因" })).toBeInTheDocument();
    expect(screen.getByText("Pc")).toBeInTheDocument();
    expect(screen.getByText("collision_probability")).toBeInTheDocument();
  });
});
