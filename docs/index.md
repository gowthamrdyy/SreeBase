---
hide:
  - navigation
  - toc
---

<div class="sb-hero">
  <div class="sb-eyebrow">Database Systems Engineering</div>
  <h1>Master databases by building one.</h1>
  <p>SreeBase is an educational, pure-Python document database with a bracketless query language. Learn how storage engines, custom parsers, and secondary indexes work under the hood without the enterprise bloat.</p>
  <div class="sb-actions">
    <a href="tutorials/installation.md" class="sb-button primary">Start Learning</a>
    <a href="syntax.md" class="sb-button">View Syntax</a>
  </div>
</div>

<div class="sb-grid two">

<div class="sb-card">
  <h3>Code as Data</h3>
  <p>Forget brackets and semicolons. SreeBase uses an elegant indentation-based query language inspired by Python, making database interactions incredibly clean.</p>
  <div class="sb-terminal">
```sql
insert into employees
    name = "Anika"
    role = "Engineering"
    salary = 90000
```
  </div>
</div>

<div class="sb-card">
  <h3>Under the Hood</h3>
  <p>Learn core concepts like append-only Bitcask storage engines, in-memory hash indexes, custom lexing/parsing, and binary TCP protocols.</p>
  <div class="sb-terminal">
```sql
get employees
    role = "Engineering"
    sort by salary desc
    limit 5
```
  </div>
</div>

</div>

## Learning Tracks

<div class="sb-grid two">

<div class="sb-track">
  <h2>1. Core Concepts</h2>
  <ul class="sb-lesson-list">
    <li>
      <a href="tutorials/installation.md"><strong>Installation & Setup</strong></a>
      <span>Get SreeBase running on your machine</span>
    </li>
    <li>
      <a href="tutorials/first-database.md"><strong>Your First Database</strong></a>
      <span>Create collections and insert records</span>
    </li>
    <li>
      <a href="syntax.md"><strong>The Bracketless Syntax</strong></a>
      <span>Master the indentation rules</span>
    </li>
    <li>
      <a href="tutorials/concepts.md"><strong>How SreeBase Works</strong></a>
      <span>Architecture and storage overview</span>
    </li>
  </ul>
</div>

<div class="sb-track">
  <h2>2. Query Mastery</h2>
  <ul class="sb-lesson-list">
    <li>
      <a href="tutorials/read.md"><strong>Reading Data</strong></a>
      <span>Filters, sorting, and limits</span>
    </li>
    <li>
      <a href="tutorials/update.md"><strong>Updating Records</strong></a>
      <span>Modifying data safely</span>
    </li>
    <li>
      <a href="tutorials/aggregations.md"><strong>Aggregations</strong></a>
      <span>Sum, Count, Avg operators</span>
    </li>
    <li>
      <a href="tutorials/indexes.md"><strong>Using Indexes</strong></a>
      <span>O(1) lookups for fast queries</span>
    </li>
  </ul>
</div>

<div class="sb-track">
  <h2>3. Build & Deploy</h2>
  <ul class="sb-lesson-list">
    <li>
      <a href="api.md"><strong>Python SDK</strong></a>
      <span>Integrate SreeBase into your apps</span>
    </li>
    <li>
      <a href="tutorials/example-app.md"><strong>Example Project</strong></a>
      <span>Build a full app with ReddyBase</span>
    </li>
    <li>
      <a href="tutorials/security.md"><strong>Security & Admin</strong></a>
      <span>Roles, users, and RBAC</span>
    </li>
  </ul>
</div>

<div class="sb-track">
  <h2>4. Resources</h2>
  <ul class="sb-lesson-list">
    <li>
      <a href="faq.md"><strong>FAQ & Common Pitfalls</strong></a>
      <span>Indentation, blank lines, & modes</span>
    </li>
    <li>
      <a href="roadmap.md"><strong>Future Roadmap</strong></a>
      <span>Joins, transactions, and beyond</span>
    </li>
    <li>
      <a href="tutorials/cheat-sheet.md"><strong>Cheat Sheet</strong></a>
      <span>Quick syntax reference</span>
    </li>
  </ul>
</div>

</div>
