// Full-bleed content; native window decorations provide the title bar.

import type { ReactNode } from "react";

interface Props {
  children: ReactNode;
}

export default function BAWindow({ children }: Props) {
  return (
    <div
      className="ba-app"
      style={{
        height: "100vh",
        width: "100vw",
        overflow: "hidden",
      }}
    >
      {children}
    </div>
  );
}
