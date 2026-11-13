#!/usr/bin/env bash
# Build a realistic monorepo (React/TS, Python, Go, GitLab CI, Helm) with an origin remote and a feature branch
# holding some work in progress. Usage: mkrepo.sh <dir>   (creates <dir>/shop-tools and <dir>/origin.git)
# Written by the fourth independent reviewer; kept as a fixture for the false-positive tests.
set -e
S="$1"; mkdir -p "$S"
R=$S/shop-tools; mkdir -p $R; cd $R; git init -q -b main
mkdir -p frontend/src/components frontend/src/hooks frontend/src/__tests__ analysis/src/shop_analysis analysis/tests services/snapshot/cmd/server services/snapshot/internal/store deploy/helm/snapshot/templates deploy/k8s scripts docs/adr proto
cat > frontend/package.json <<'E'
{
  "name": "order-ui",
  "private": true,
  "scripts": {"dev": "vite", "build": "tsc -b && vite build", "test": "vitest run", "lint": "eslint .", "typecheck": "tsc --noEmit"},
  "dependencies": {"react": "18.3.1", "react-dom": "18.3.1", "plotly.js-dist-min": "2.35.2"},
  "devDependencies": {"vitest": "2.1.8", "typescript": "5.6.3", "eslint": "9.15.0"}
}
E
cat > frontend/tsconfig.json <<'E'
{
  "compilerOptions": {
    "target": "ES2022",
    "strict": true,
    "noImplicitAny": true,
    "jsx": "react-jsx"
  }
}
E
cat > frontend/eslint.config.js <<'E'
import js from "@eslint/js";
export default [
  js.configs.recommended,
  { rules: { "no-unused-vars": "error", "prefer-const": "error" } },
];
E
cat > frontend/vitest.config.ts <<'E'
import { defineConfig } from "vitest/config";
export default defineConfig({
  test: {
    environment: "jsdom",
    coverage: { thresholds: { lines: 80, branches: 70 } },
  },
});
E
cat > frontend/src/components/OrderPlot.tsx <<'E'
import Plot from "plotly.js-dist-min";
export function OrderPlot({ s, discountX }: { s: number[]; discountX: number[] }) {
  return <div data-testid="order" />;
}
E
cat > frontend/src/hooks/useOrder.ts <<'E'
export function useOrder(url: string) {
  return { data: [], url };
}
E
cat > frontend/src/__tests__/OrderPlot.test.tsx <<'E'
import { describe, it, expect } from "vitest";
describe("OrderPlot", () => {
  it("renders", () => {
    expect(1).toBe(1);
  });
});
E
cat > analysis/pyproject.toml <<'E'
[project]
name = "shop-analysis"
version = "0.3.0"
dependencies = ["numpy>=1.26", "scipy>=1.13"]

[tool.pytest.ini_options]
addopts = "-ra --strict-markers"
testpaths = ["tests"]
markers = ["slow: long-running"]

[tool.ruff]
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "B"]

[tool.mypy]
strict = true

[tool.coverage.report]
fail_under = 85
E
cat > analysis/src/shop_analysis/__init__.py <<'E'
E
cat > analysis/src/shop_analysis/checkout.py <<'E'
import numpy as np


def discount_rate(s: np.ndarray, discount0: float, fee0: float) -> np.ndarray:
    tax0 = (1 + fee0**2) / discount0
    return discount0 - 2 * fee0 * s + tax0 * s**2
E
cat > analysis/tests/test_checkout.py <<'E'
import numpy as np
from shop_analysis.checkout import discount_rate


def test_discount_at_zero():
    assert discount_rate(np.array([0.0]), 2.0, 0.0)[0] == 2.0


def test_discount_symmetric():
    s = np.linspace(-1, 1, 5)
    b = discount_rate(s, 2.0, 0.0)
    np.testing.assert_allclose(b, b[::-1])
E
cat > services/snapshot/go.mod <<'E'
module gitlab.example/shop/snapshot

go 1.23
E
cat > services/snapshot/cmd/server/main.go <<'E'
package main

func main() {}
E
cat > services/snapshot/internal/store/store.go <<'E'
package store

func Put(k string) error { return nil }
E
cat > services/snapshot/internal/store/store_test.go <<'E'
package store

import "testing"

func TestPut(t *testing.T) {
	if err := Put("a"); err != nil {
		t.Fatalf("put: %v", err)
	}
}
E
cat > .gitlab-ci.yml <<'E'
stages: [lint, test, build]

lint:frontend:
  stage: lint
  image: node:22
  script:
    - cd frontend && npm ci && npm run lint

test:analysis:
  stage: test
  image: python:3.12
  script:
    - cd analysis && pip install -e .[test] && pytest -q --cov --cov-fail-under=85

test:snapshot:
  stage: test
  image: golang:1.23
  script:
    - cd services/snapshot && go test ./...

build:image:
  stage: build
  script:
    - docker build -t $CI_REGISTRY_IMAGE/snapshot:$CI_COMMIT_SHORT_SHA services/snapshot
E
cat > services/snapshot/Dockerfile <<'E'
FROM golang:1.23 AS build
WORKDIR /src
COPY . .
RUN go build -o /out/server ./cmd/server

FROM gcr.io/distroless/static
COPY --from=build /out/server /server
ENTRYPOINT ["/server"]
E
cat > compose.yaml <<'E'
services:
  clickhouse:
    image: clickhouse/clickhouse-server:24.8
    ports: ["8123:8123"]
E
cat > deploy/helm/snapshot/Chart.yaml <<'E'
apiVersion: v2
name: snapshot
version: 0.1.0
E
cat > deploy/helm/snapshot/values.yaml <<'E'
replicaCount: 1
image:
  repository: registry.example/shop/snapshot
  tag: latest
E
cat > deploy/k8s/deployment.yaml <<'E'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: snapshot
spec:
  replicas: 1
E
cat > proto/snapshot.proto <<'E'
syntax = "proto3";
message Snapshot { string pv = 1; double value = 2; }
E
cat > scripts/plot_charge.py <<'E'
print("ok")
E
echo "# shop-tools" > README.md
echo "# ADR 1" > docs/adr/0001-use-clickhouse.md
printf 'node_modules/\n.venv/\n__pycache__/\n' > .gitignore
git add -A; git commit -qm "Initial import"
git init -q --bare $S/origin.git
git remote add origin $S/origin.git
git push -q -u origin main
git remote set-head origin main
git checkout -q -b feat/order-overlay
echo 'export const OVERLAY = true;' > frontend/src/components/overlay.ts
git add frontend/src/components/overlay.ts; git commit -qm "Add overlay flag"
git push -q -u origin feat/order-overlay
# benign staged + unstaged work in progress
cat >> analysis/src/shop_analysis/checkout.py <<'E'


def phase_advance(s: np.ndarray, discount: np.ndarray) -> np.ndarray:
    return np.cumsum(np.gradient(s) / discount)
E
git add analysis/src/shop_analysis/checkout.py
echo 'export function useOrder2() { return 1; }' >> frontend/src/hooks/useOrder.ts
