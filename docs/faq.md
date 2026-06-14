# FAQ & Common Pitfalls

Welcome to SreeBase! Because SreeBase features a unique bracketless query language, first-time users often run into a couple of common syntax pitfalls. 

## 1. Why does my query show `...` and not run when I press Enter?

**SreeBase queries are multi-line.** Since there are no curly braces `{}` or semicolons `;` that hard-terminate a query block, the shell does not automatically know when you have finished typing.

When you type a query and press `Enter`, the shell prompts you with `...` to allow you to add more filters, assignments, or limits on the next line.

**How to fix it:**
To execute the query, simply press `Enter` **twice** at the end of your query (i.e., submit an empty line).

```text
sreebase> get cast
      ...                     <-- Press Enter on this blank line!
```

## 2. I get a `[ParserError] Expected indented assignments` when inserting

This happens because SreeBase relies entirely on **indentation** to understand which block a line belongs to (exactly like Python). 

The `...` prompt is just a visual indicator; it does not add physical spaces to your query. 

**Incorrect (0 indentation):**
```sql
sreebase> insert into users
      ... name="gowtham"      <-- Error: Expected indentation
```

**Correct (Indented with Spaces):**
You must press the Spacebar (e.g., 4 spaces) before typing the assignment.
```sql
sreebase> insert into users
      ...     name="gowtham"  <-- Correct!
```

## 3. Should I use `sreebase serve` or `sreebase local`?

- Use **`sreebase local`** for rapid prototyping, learning, and single-terminal usage. It functions exactly like SQLite, running the embedded database engine directly in your terminal.
- Use **`sreebase serve`** when you are running an actual application (using the Python SDK) or you want multiple clients to connect to the database simultaneously over TCP. Remember, `serve` occupies the terminal, so you must use a second terminal window to run `sreebase shell`.

## 4. How do I quit the shell?

Type `exit`, `quit`, `\q`, or press `Ctrl+D` to safely exit the interactive REPL.
