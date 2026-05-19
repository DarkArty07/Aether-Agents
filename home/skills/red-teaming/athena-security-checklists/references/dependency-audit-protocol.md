# Dependency Audit Protocol

When Hermes requests a dependency audit:

1. **Identify critical dependencies**: From `package.json`, `pyproject.toml`, or `requirements.txt`
2. **For each critical dependency** (auth, crypto, DB adapter, web framework):
   - Note current version
   - Check for known CVEs: `npm audit`, `pip audit`, or request Etalides to research
   - Check maintenance: releases in last 12 months, active maintainer, open issues ratio
3. **Prioritize**: Critical > High > Medium > Low
4. **If CVE research needed**: Ask Hermes to route to Etalides. Do NOT do web research yourself.