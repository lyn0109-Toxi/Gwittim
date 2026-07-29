import { spawnSync } from "node:child_process";

const checks = [
  ["node", ["--check", "apps/api/server.mjs"]],
  ["node", ["--check", "apps/web/app.js"]],
  ["python3", ["-B", "-m", "py_compile", "streamlit_app.py"]],
];

for (const [command, args] of checks) {
  const result = spawnSync(command, args, { stdio: "inherit" });

  if (result.error?.code === "ENOENT" && command === "python3") {
    console.log("Skipping Streamlit syntax check because python3 is not installed.");
    continue;
  }

  if (result.status !== 0) {
    process.exit(result.status || 1);
  }
}
