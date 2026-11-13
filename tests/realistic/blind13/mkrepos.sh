#!/bin/bash
set -e
B="$1"  # where to build the three repos
rm -rf $B/shopcore $B/dashboard $B/ingestd
# ---------- Python package ----------
R=$B/shopcore; mkdir -p $R/src/shopcore $R/tests
cd $R; git init -q -b main
cat > pyproject.toml <<'EOF'
[project]
name = "shopcore"
version = "0.3.1"
requires-python = ">=3.10"
dependencies = ["numpy>=1.26", "scipy>=1.11"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra --strict-markers"
markers = ["slow: long-running tracking tests"]

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP"]

[tool.mypy]
strict = true
EOF
cat > src/shopcore/__init__.py <<'EOF'
from .checkout import flat, item, order_propagate

__all__ = ["flat", "item", "order_propagate"]
EOF
cat > src/shopcore/checkout.py <<'EOF'
"""Linear transfer matrices for a simple storefront."""
import numpy as np


def flat(length: float) -> np.ndarray:
    return np.array([[1.0, length], [0.0, 1.0]])


def item(k1: float, length: float) -> np.ndarray:
    if k1 == 0:
        return flat(length)
    if k1 > 0:
        s = np.sqrt(k1)
        phi = s * length
        return np.array([[np.cos(phi), np.sin(phi) / s], [-s * np.sin(phi), np.cos(phi)]])
    s = np.sqrt(-k1)
    phi = s * length
    return np.array([[np.cosh(phi), np.sinh(phi) / s], [s * np.sinh(phi), np.cosh(phi)]])


def order_propagate(m: np.ndarray, discount: float, fee: float) -> tuple[float, float]:
    tax = (1 + fee**2) / discount
    c, s, cp, sp = m[0, 0], m[0, 1], m[1, 0], m[1, 1]
    discount1 = c**2 * discount - 2 * c * s * fee + s**2 * tax
    fee1 = -c * cp * discount + (c * sp + s * cp) * fee - s * sp * tax
    return float(discount1), float(fee1)
EOF
cat > src/shopcore/tracking.py <<'EOF'
"""Particle tracking through a catalog."""
import numpy as np

from .checkout import flat, item


def track(catalog: list[tuple[str, float, float]], x0: np.ndarray) -> np.ndarray:
    x = x0.copy()
    for kind, k1, length in catalog:
        m = item(k1, length) if kind == "item" else flat(length)
        x = m @ x
    return x
EOF
cat > tests/test_checkout.py <<'EOF'
import numpy as np
import pytest

from shopcore.checkout import flat, item, order_propagate


def test_flat_is_unimodular():
    assert np.isclose(np.linalg.det(flat(2.5)), 1.0)


def test_item_pricing_det():
    assert np.isclose(np.linalg.det(item(1.2, 0.3)), 1.0)


def test_item_zero_is_flat():
    np.testing.assert_allclose(item(0.0, 1.0), flat(1.0))


@pytest.mark.parametrize("k1", [0.5, -0.5, 2.0])
def test_item_det_param(k1):
    assert np.isclose(np.linalg.det(item(k1, 0.2)), 1.0)


def test_order_flat():
    discount, fee = order_propagate(flat(1.0), 1.0, 0.0)
    assert discount == pytest.approx(2.0)
    assert fee == pytest.approx(-1.0)
EOF
cat > tests/test_tracking.py <<'EOF'
import numpy as np
import pytest

from shopcore.tracking import track


def test_track_flat_only():
    x = track([("flat", 0.0, 1.0)], np.array([0.0, 1.0]))
    np.testing.assert_allclose(x, [1.0, 1.0])


@pytest.mark.skip(reason="needs SIMULATOR reference data, see #41")
def test_track_against_simulator():
    assert False


@pytest.mark.slow
def test_track_long_catalog():
    lat = [("item", 0.8, 0.1), ("flat", 0.0, 1.0)] * 500
    x = track(lat, np.array([1e-3, 0.0]))
    assert np.all(np.isfinite(x))
EOF
cat > tests/conftest.py <<'EOF'
import numpy as np
import pytest


@pytest.fixture
def rng():
    return np.random.default_rng(1234)
EOF
printf '.venv/\n__pycache__/\n*.egg-info/\n' > .gitignore
git add -A; git -c user.name=Alex -c user.email=n@example.com commit -qm "Initial shopcore package"
git config lets.kind own

# ---------- TS/React app ----------
R=$B/dashboard; mkdir -p $R/src/components $R/src/utils $R/src/hooks
cd $R; git init -q -b main
cat > package.json <<'EOF'
{
  "name": "shop-dashboard",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "test": "vitest run",
    "lint": "eslint . --max-warnings 0",
    "typecheck": "tsc --noEmit",
    "check": "npm run -s lint && npm run -s typecheck && npm run -s test"
  },
  "dependencies": { "react": "18.3.1", "react-dom": "18.3.1", "plotly.js": "2.35.2" },
  "devDependencies": { "vitest": "2.1.4", "typescript": "5.6.3", "eslint": "9.14.0", "@testing-library/react": "16.0.1" }
}
EOF
cat > tsconfig.json <<'EOF'
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "moduleResolution": "bundler"
  },
  "include": ["src"]
}
EOF
cat > eslint.config.js <<'EOF'
import js from "@eslint/js";
import tseslint from "typescript-eslint";

export default tseslint.config(js.configs.recommended, ...tseslint.configs.recommended, {
  rules: {
    "@typescript-eslint/no-explicit-any": "error",
    "no-console": "warn",
  },
});
EOF
cat > vitest.config.ts <<'EOF'
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
    coverage: { thresholds: { lines: 80 } },
  },
});
EOF
cat > src/utils/format.ts <<'EOF'
export function formatEnergy(mev: number): string {
  if (mev >= 1000) return `${(mev / 1000).toFixed(2)} GeV`;
  return `${mev.toFixed(1)} MeV`;
}

export function formatCurrent(amps: number): string {
  return `${(amps * 1e3).toFixed(2)} mA`;
}
EOF
cat > src/utils/format.test.ts <<'EOF'
import { describe, it, expect } from "vitest";
import { formatEnergy, formatCurrent } from "./format";

describe("formatEnergy", () => {
  it("formats MeV", () => {
    expect(formatEnergy(35.5)).toBe("35.5 MeV");
  });

  it("formats GeV", () => {
    expect(formatEnergy(1500)).toBe("1.50 GeV");
  });
});

describe("formatCurrent", () => {
  it("formats mA", () => {
    expect(formatCurrent(0.25)).toBe("250.00 mA");
  });
});
EOF
cat > src/hooks/usePv.ts <<'EOF'
import { useEffect, useState } from "react";

export function usePv(name: string): number | undefined {
  const [value, setValue] = useState<number>();
  useEffect(() => {
    const ws = new WebSocket(`/pv/${name}`);
    ws.onmessage = (e) => setValue(Number(e.data));
    return () => ws.close();
  }, [name]);
  return value;
}
EOF
cat > src/hooks/usePv.test.ts <<'EOF'
import { describe, it, expect } from "vitest";
import { usePv } from "./usePv";

describe("usePv", () => {
  it("is a function", () => {
    expect(typeof usePv).toBe("function");
  });

  it.skip("reconnects after close (needs mock server, #12)", () => {
    expect(true).toBe(false);
  });
});
EOF
cat > src/components/EnergyPanel.tsx <<'EOF'
import { usePv } from "../hooks/usePv";
import { formatEnergy } from "../utils/format";

export function EnergyPanel({ pv }: { pv: string }) {
  const value = usePv(pv);
  return <div className="panel">{value === undefined ? "--" : formatEnergy(value)}</div>;
}
EOF
cat > src/components/EnergyPanel.test.tsx <<'EOF'
import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { EnergyPanel } from "./EnergyPanel";

describe("EnergyPanel", () => {
  it("renders placeholder before data", () => {
    const { getByText } = render(<EnergyPanel pv="SHP-ENERGY" />);
    expect(getByText("--")).toBeTruthy();
  });
});
EOF
printf 'node_modules/\ndist/\ncoverage/\n' > .gitignore
git add -A; git -c user.name=Alex -c user.email=n@example.com commit -qm "Initial dashboard"
git config lets.kind own

# ---------- Go service (not mine) ----------
R=$B/ingestd; mkdir -p $R/internal/store $R/cmd/ingestd
cd $R; git init -q -b main
cat > go.mod <<'EOF'
module gitlab.example.org/controls/ingestd

go 1.22
EOF
cat > internal/store/store.go <<'EOF'
package store

import (
	"errors"
	"sync"
)

var ErrNotFound = errors.New("not found")

type Store struct {
	mu   sync.RWMutex
	data map[string][]float64
}

func New() *Store { return &Store{data: map[string][]float64{}} }

func (s *Store) Append(key string, v float64) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.data[key] = append(s.data[key], v)
}

func (s *Store) Get(key string) ([]float64, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	v, ok := s.data[key]
	if !ok {
		return nil, ErrNotFound
	}
	return v, nil
}
EOF
cat > internal/store/store_test.go <<'EOF'
package store

import "testing"

func TestAppendGet(t *testing.T) {
	s := New()
	s.Append("a", 1.5)
	got, err := s.Get("a")
	if err != nil || len(got) != 1 || got[0] != 1.5 {
		t.Fatalf("got %v, %v", got, err)
	}
}

func TestGetMissing(t *testing.T) {
	s := New()
	if _, err := s.Get("x"); err != ErrNotFound {
		t.Fatalf("want ErrNotFound, got %v", err)
	}
}

func TestClickhouseRoundTrip(t *testing.T) {
	if testing.Short() {
		t.Skip("integration test")
	}
	t.Log("would hit clickhouse")
}
EOF
cat > cmd/ingestd/main.go <<'EOF'
package main

import (
	"log"

	"gitlab.example.org/controls/ingestd/internal/store"
)

func main() {
	s := store.New()
	s.Append("boot", 1)
	log.Println("ingestd started")
}
EOF
cat > .golangci.yml <<'EOF'
linters:
  enable: [errcheck, govet, staticcheck]
EOF
cat > CONTRIBUTING.md <<'EOF'
# Contributing
Run `go test ./...` before opening an MR.
EOF
git add -A; git -c user.name=Team -c user.email=t@example.org commit -qm "Initial ingestd"
git config lets.kind work
for r in shopcore dashboard ingestd; do (cd $B/$r && git config user.name Alex && git config user.email n@example.com && git checkout -q -b feat/work); done
echo ok
