# Admin And Security

SreeBase includes basic authentication and role-based access control.

## Bootstrap The First Admin

On a fresh database:

```sql
create user admin password "supersecret" role admin
```

This is allowed only when no users exist.

## Login

```sql
login admin password "supersecret"
```

## Roles

| Role | Purpose |
| --- | --- |
| `admin` | Full access, including user creation and `_system.*` collections |
| `read` | Read-only access to normal collections |

Create a read-only user:

```sql
create user analyst password "readonlypass" role read
```

## Password Storage

SreeBase stores passwords as salted PBKDF2-HMAC hashes. It does not store new passwords as plaintext.

Older plaintext user records are migrated after a successful login.

## System Collections

Internal collections start with `_system.`.

Non-admin users cannot access them.

## Current Security Limits

SreeBase is still a learning project. It does not currently provide:

- TLS for the TCP protocol
- login rate limiting
- account lockout
- audit logs
- encryption at rest
- collection-level permission policies

Use it on localhost or trusted private networks unless you add those protections.

