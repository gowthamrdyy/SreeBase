---
hide:
  - navigation
  - toc
---

<div style="text-align: center; margin-top: 4rem; margin-bottom: 4rem;">
  <h1 style="font-size: 3.5rem; font-weight: 800; letter-spacing: -0.05em; color: var(--md-primary-fg-color);">SreeBase</h1>
  <p style="font-size: 1.5rem; color: var(--md-default-fg-color--light); max-width: 600px; margin: 0 auto 2rem auto;">
    A lightning-fast, educational document database with a beautiful bracketless query language.
  </p>
  <a href="tutorials/index.md" class="md-button md-button--primary" style="font-size: 1.2rem; padding: 0.5rem 2rem;">Get Started</a>
  <a href="faq.md" class="md-button" style="font-size: 1.2rem; padding: 0.5rem 2rem;">Read FAQ</a>
</div>

## Why SreeBase?

SreeBase is built from scratch in Python to demystify how databases actually work under the hood. It skips the bloated enterprise features in favor of pure, readable systems engineering.

<div class="grid cards" markdown>

-   :material-code-brackets: **Bracketless Query Language**

    ---

    Forget `{}` and `;`. SreeBase uses an elegant, indentation-based parser inspired by Python.

-   :material-database-sync: **Bitcask Storage Engine**

    ---

    Writes are blindingly fast append-only logs. Reads are O(1) guaranteed via in-memory hash indexes.

-   :material-server-network: **TCP Server & Local Shell**

    ---

    Run a standalone server with Role-Based Access Control, or boot directly into a SQLite-style embedded local shell.

-   :material-language-python: **Native Python SDK**

    ---

    Integrate SreeBase directly into your Python apps with our secure, injection-protected `reddybase` driver.

</div>

---

## ⚡ A First Query

```sql
insert into employees
    name = "Anika"
    department = "Engineering"
    salary = 90000
```

```sql
get employees
    department = "Engineering"
    sort by salary desc
    limit 5
```

## 🗺️ Learning Path

1. **[Install SreeBase](tutorials/installation.md)**
2. **[Create your first database](tutorials/first-database.md)**
3. **[Learn the bracketless syntax](syntax.md)**
4. **[Review the Future Roadmap](roadmap.md)**

