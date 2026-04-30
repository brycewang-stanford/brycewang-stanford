# Bryce Wang

> Causal inference & econometrics. Founder of [StatsPAI](https://github.com/brycewang-stanford/StatsPAI) and [CoPaper.AI](https://www.copaper.ai). Data Scientist @ Stanford REAP.

---

## StatsPAI ⭐

**Production Python library for causal inference & econometrics — 925 functions across 79 submodules.**

`pip install statspai`

- **Methods:** DiD / IV / RD / synthetic control / DML / meta-learners / Bayesian / causal discovery / structural econometrics / panel data / spatial / conformal / TMLE / BCF / dose-response / bounds / spillover
- **Design:** Agent-native — every function returns structured results with self-describing schema; humans and AI agents use the same API
- **Ecosystem:** 10K+ monthly PyPI downloads · Research labs at Stanford, MIT, NBER, Berkeley · Registered in PyPI, cited in academic projects

```python
import statspai as sp

# Estimate heterogeneous treatment effects with DR-Learner
result = sp.metalearner(y="wage", treatment="college", covariates=["age", "exp", "educ"],
                         method="dr", data_path="cps.toml")
result.summary()
```

**[→ StatsPAI on GitHub](https://github.com/brycewang-stanford/StatsPAI)** · **[→ PyPI](https://pypi.org/project/StatsPAI/)**

---

## CoPaper.AI 🏗️

**AI-powered causal inference research platform — from raw data to publishable manuscript.**

CoPaper.AI is built on StatsPAI's estimator stack. It integrates LLMs for automated econometric workflow generation, from dataset ingestion → estimator selection → inference → reproducible paper output. Used by empirical researchers who need to move fast without sacrificing numerical rigor.

**[→ CoPaper.AI](https://www.copaper.ai)**

---

## Awesome-Agent-Skills 📚

**23,000+ curated agent skills for empirical research across 8 disciplines.**

End-to-end: data cleaning → causal identification → estimation → robustness checks → manuscript. Powers CoPaper.AI's agent-native research workflow.

**[→ GitHub](https://github.com/brycewang-stanford/Awesome-Agent-Skills-for-Empirical-Research)** · 521 stars

---

## Research & Engineering Background

- **Domain:** Causal inference, econometrics, empirical microeconomics
- **Stack:** Python (pandas, numpy, scipy, scikit-learn, statsmodels, pyfixest) · Rust (PyO3 HDFE backend) · PyTorch · PostgreSQL · AWS/GCP
- **Infrastructure:** Building data pipelines that process research datasets → analysis-ready formats · ETL automation · privacy-preserving analytic tooling
- **Alignment:** Familiar with AI safety research workflows; StatsPAI's robust estimator stack is directly relevant to measuring AI's economic impact

---

Data Scientist @ **Stanford REAP** · [Email](mailto:brycew6m@stanford.edu) · [GitHub](https://github.com/brycewang-stanford)
